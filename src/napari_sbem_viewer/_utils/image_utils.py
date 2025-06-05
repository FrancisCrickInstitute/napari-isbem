import glob
import os

import cv2
import dask
import dask.array as da
import numpy as np
import scipy.ndimage as ndi
import SimpleITK as sitk
import zarr
from ome_zarr.io import parse_url
from ome_zarr.writer import write_multiscale
from skimage.io.collection import alphanumeric_key
from skimage.transform import downscale_local_mean
from tifffile import TiffWriter, imread


def save_tiff(
    filename,
    image,
    metadata=None,
    compression=None,
    pyramid_levels=3,
    bigtiff=True,
):
    if len(image.shape) == 3:
        h, w, s = image.shape
        photometric = 'RGB'
    else:
        h, w = image.shape
        photometric = 'minisblack'
    with TiffWriter(filename, bigtiff=bigtiff) as tif:
        if metadata is not None:
            tif.write(
                image,
                tile=(256, 256),
                photometric=photometric,
                subifds=pyramid_levels,
                compression=compression,
                metadata=metadata,
            )
        else:
            tif.write(
                image,
                tile=(256, 256),
                photometric=photometric,
                subifds=pyramid_levels,
                compression=compression,
            )

        for i in range(pyramid_levels):
            w = int(np.round(w / 4))
            h = int(np.round(h / 4))
            image = cv2.resize(
                image, dsize=(w, h), interpolation=cv2.INTER_LINEAR
            )

            tif.write(
                image,
                tile=(256, 256),
                photometric=photometric,
                compression=compression,
                subfiletype=i + 1,
            )


def convert_to_micrometers(value, unit):
    conversions = {
        'nm': 1e-3,
        'µm': 1,
        'um': 1,
        'mm': 1e3,
        'cm': 1e4,
        'm': 1e6,
    }
    value = value * conversions.get(unit, 1)
    return value


def get_ome_pixel_size(metadata, axis):
    axis = axis.upper()
    if axis not in ['X', 'Y', 'Z']:
        raise ValueError("Invalid axis. Must be one of 'X', 'Y', 'Z'")
    pixel_size = metadata['OME']['Image']['Pixels'][f'PhysicalSize{axis}']
    units = metadata['OME']['Image']['Pixels'][f'PhysicalSize{axis}Unit']
    return convert_to_micrometers(pixel_size, units)


def get_ome_position(metadata, axis):
    axis = axis.upper()
    if axis not in ['X', 'Y', 'Z']:
        raise ValueError("Invalid axis. Must be one of 'X', 'Y', 'Z'")
    pixel_size = metadata['OME']['Image']['Pixels']['Plane'][f'Position{axis}']
    units = metadata['OME']['Image']['Pixels']['Plane'][f'Position{axis}Unit']
    return convert_to_micrometers(pixel_size, units)


def load_as_dask(tiff, dtype):
    arrays = []
    for level in range(len(tiff.pages)):
        data = dask.delayed(load_pyramid_slice)(tiff, level)
        arrays.append(
            da.from_delayed(data, shape=tiff.pages[level].shape, dtype=dtype)
        )
    return arrays


def load_pyramid_slice(tiff, level):
    data = da.from_zarr(tiff.aszarr(level=level))
    if data.chunksize == data.shape:
        data = data.rechunk()
    return data


def get_dask_stack(image_dir, ext='tif'):
    filenames = sorted(
        glob(os.path.join(image_dir, f'*.{ext}')), key=alphanumeric_key
    )
    # read the first file to get the shape and dtype
    # ASSUMES THAT ALL FILES SHARE THE SAME SHAPE/TYPE
    sample = imread(filenames[0])

    lazy_imread = dask.delayed(imread)  # lazy reader
    lazy_arrays = [lazy_imread(fn) for fn in filenames]
    dask_arrays = [
        da.from_delayed(delayed_reader, shape=sample.shape, dtype=sample.dtype)
        for delayed_reader in lazy_arrays
    ]
    # Stack into one large dask.array
    return da.stack(dask_arrays, axis=0)


def create_image_pyramid(image, downsample_factor, pyramid_levels):
    pyramid = [image]
    for i in range(pyramid_levels):
        pyramid.append(downsample_3d_image_sitk(pyramid[i], downsample_factor))
    return pyramid


def downsample_3d_image_sitk(image, downsample_factor):
    if isinstance(downsample_factor, int):
        downsample_factor = (
            downsample_factor,
            downsample_factor,
            downsample_factor,
        )
    elif len(downsample_factor) != 3:
        raise ValueError(
            'downsample_factor must be an int or a tuple of three ints.'
        )

    sitk_image = sitk.GetImageFromArray(image.astype(np.float32))
    original_spacing = sitk_image.GetSpacing()
    new_spacing = [
        original_spacing[i] * downsample_factor[i] for i in range(3)
    ]
    original_size = sitk_image.GetSize()
    new_size = [int(original_size[i] / downsample_factor[i]) for i in range(3)]

    resample = sitk.ResampleImageFilter()
    resample.SetOutputSpacing(new_spacing)
    resample.SetSize(new_size)
    resample.SetInterpolator(sitk.sitkLinear)
    downsampled_image_sitk = resample.Execute(sitk_image)

    return sitk.GetArrayFromImage(downsampled_image_sitk).astype(image.dtype)


def downsample_3d_image(image, downsample_factor):
    if isinstance(downsample_factor, int):
        downsample_factor = (
            downsample_factor,
            downsample_factor,
            downsample_factor,
        )
    elif len(downsample_factor) != 3:
        raise ValueError('Factor must be an int or a tuple of three ints.')

    downsampled_image = downscale_local_mean(image, factors=downsample_factor)
    return downsampled_image


def merge_nearby_objects(mask, tolerance):
    mask_dilated = dilate_with_sphere_sitk(mask > 0, round(tolerance / 2))
    mask_dilated = connected_components_sitk(mask_dilated.astype(np.uint8))
    mask_dilated[mask == 0] = 0
    return mask_dilated


def dilate_with_sphere_sitk(mask, radius):
    if mask.ndim != 3:
        raise ValueError('Input array must be 3-dimensional.')

    sitk_image = sitk.GetImageFromArray(mask.astype(np.uint8))
    structuring_element = sitk.sitkBall
    dilated_mask = sitk.BinaryDilate(
        sitk_image, (radius, radius, radius), structuring_element
    )
    return sitk.GetArrayFromImage(dilated_mask).astype(mask.dtype)


def connected_components_sitk(mask):
    if mask.ndim != 3:
        raise ValueError('Input mask must be 3-dimensional.')

    sitk_image = sitk.GetImageFromArray(mask.astype(np.uint8))
    labeled_mask = sitk.ConnectedComponent(sitk_image)
    return sitk.GetArrayFromImage(labeled_mask).astype(mask.dtype)


def convert_to_uint8(image):
    # if image.dtype == np.uint8:
    #     image = image
    # elif image.dtype == np.uint16:
    #     image = image
    if image.dtype == np.float32:
        image = image * 255
    return image.astype(np.uint8)


def create_ome_metadata(scales, name, unit='micrometer'):
    metadata = {
        'name': name,
        'axes': [
            {'name': 'z', 'type': 'space', 'unit': unit},
            {'name': 'y', 'type': 'space', 'unit': unit},
            {'name': 'x', 'type': 'space', 'unit': unit},
        ],
        'datasets': [],
    }
    for i, scale in enumerate(scales):
        dataset_metadata = {
            'path': f'{i}',
            'coordinateTransformations': [
                {'type': 'scale', 'scale': [scale[0], scale[1], scale[2]]}
            ],
        }
        metadata['datasets'].append(dataset_metadata)
    return [metadata]


def save_ome_zarr(save_path, image_pyramid, chunksize, scales, name):
    store = parse_url(save_path, mode='w').store
    root = zarr.group(store=store)
    write_multiscale(
        pyramid=image_pyramid,
        group=root,
        axes='zyx',
        storage_options={'chunks': chunksize},
    )
    metadata = create_ome_metadata(scales, name)
    root.attrs['multiscales'] = metadata


def get_bounds_from_labels(labels):
    # Given a labeled mask, return the upper and lower bounds of each label
    assert labels.dtype == np.uint8
    slices = ndi.find_objects(labels)
    bounds = []
    label_ids = []
    for i, slice_ in enumerate(slices):
        if slice_ is None:
            continue
        mins = np.asarray([s.start for s in slice_])
        maxes = np.asarray([s.stop for s in slice_])
        bounds.append([mins, maxes])
        label_ids.append(i + 1)
    return bounds, label_ids


def get_pyramid_scales(scale, shapes):
    """Using the top level scale and shapes of an image pyramid,
    calculate the scales of all pyramid levels."""
    for shape in shapes:
        assert len(scale) == len(shape)
    all_scales = [scale]
    for shape in shapes[1:]:
        current_scale = []
        for i in range(len(scale)):
            factor = shape[0] / shape[i]
            current_scale.append(scale[0] * factor)
        all_scales.append(tuple(current_scale))
    return all_scales


def convert_data_to_world_coords(layer, points):
    world_coords = []
    for point in points:
        world_coords.append(layer.data_to_world(point))
    return np.asarray(world_coords)
