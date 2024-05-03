from tifffile import TiffWriter
import socket
import json
import cv2
import numpy as np
from qtpy.QtWidgets import QErrorMessage
from qtpy.QtCore import QObject, Signal
from queue import Queue
import math
import dask.array as da
import dask
import os
import glob
from skimage.io.collection import alphanumeric_key
from tifffile import imread


def save_tiff(filename, image, metadata=None, compression=None, pyramid_levels=3, bigtiff=True):
    if len(image.shape) == 3:
        h, w, s = image.shape
        photometric = "RGB"
    else:
        h, w = image.shape
        photometric = "minisblack"
    with TiffWriter(filename, bigtiff=bigtiff) as tif:
        if metadata is not None:
            tif.write(
                image,
                tile=(256, 256),
                photometric=photometric,
                subifds=pyramid_levels,
                compression=compression,
                metadata=metadata
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
            image = cv2.resize(image, dsize=(w, h), interpolation=cv2.INTER_LINEAR)

            tif.write(
                image,
                tile=(256, 256),
                photometric=photometric,
                compression=compression,
                subfiletype=i+1
            )
            
            
def convert_to_micrometers(value, unit):
    conversions = {'nm': 1e-3, 'µm': 1, 'um': 1, 'mm': 1e3, 'cm': 1e4, 'm': 1e6}
    value = value * conversions.get(unit, 1)
    return value


def get_ome_pixel_size(metadata, axis):
    axis = axis.upper()
    if axis not in ['X', 'Y', 'Z']:
        raise ValueError("Invalid axis. Must be one of 'X', 'Y', 'Z'")
    pixel_size = metadata['OME']['Image']['Pixels'][f'PhysicalSize{axis}']
    units = metadata['OME']['Image']['Pixels'][f'PhysicalSize{axis}Unit']
    return convert_to_micrometers(pixel_size, units)
    

def display_qt_error(parent, error):
        """Handle when an error occurs

        Show the error in an error message window.
        """
        em = QErrorMessage(parent)
        em.showMessage(str(error))
        
        
class Trigger(QObject):
    """A custom QObject for receiving notifications and commands from threads.
    The trigger signal is emitted by calling signal.emit(). The queue can
    be used to send commands: queue.put(cmd) puts a cmd into the
    queue, and queue.get() reads the cmd and empties the queue.
    """
    signal = Signal()
    queue = Queue()

    def transmit(self, req):
        """Transmit a single command."""
        self.queue.put(req)
        self.signal.emit()
        

def is_multiple(a, b):
    """
    Returns True if b is a multiple of a, False otherwise.
    """
    ratio = a / b
    return math.isclose(ratio, round(ratio))


def load_as_dask(tiff, dtype):
    arrays = []
    for level in range(len(tiff.pages)):
        data = dask.delayed(load_pyramid_slice)(tiff, level)
        arrays.append(da.from_delayed(data, shape=tiff.pages[level].shape, dtype=dtype))
    return arrays


def load_pyramid_slice(tiff, level):
    data = da.from_zarr(tiff.aszarr(level=level))
    if data.chunksize == data.shape:
        data = data.rechunk()
    return data
        

def get_dask_stack(image_dir, ext='tif'):
    filenames = sorted(glob(os.path.join(image_dir, f'*.{ext}')), key=alphanumeric_key)
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


def get_transformation_matrix_2d(moving_points, fixed_points):
    # convert coordinates from (y, x) to (x, y)
    fixed_points = fixed_points[:, ::-1]
    moving_points = moving_points[:, ::-1]
    Rt, _ = cv2.estimateAffine2D(moving_points, fixed_points)
    Rt = np.vstack([[Rt[0, 0], Rt[0, 1], Rt[1, 2]], 
                    [Rt[1, 0], Rt[1, 1], Rt[0, 2]], 
                    [0, 0, 1]])
    return Rt


def get_transformation_matrix_3d(reverse, z_offset, pts_fixed, pts_moving, scale=None):
    pass


def get_transformation_matrix_slices(reverse, z_offset, pts_fixed, pts_moving, scale=None):
    T = np.eye(4)
    
    # scale transformation to offset the x and y scaling
    if scale is not None:
        T[1, 1] = scale[0]
        T[2, 2] = scale[1]
    
    if reverse:
        T[0, 0] *= -1  # flip z-axis
    
    if z_offset != 0:
        T[0, 3] -= z_offset  # shift image to align with fixed image
    
    if pts_fixed is not None and pts_moving is not None:
        T_2d = get_transformation_matrix_2d(pts_moving, pts_fixed)
        print(T_2d)
        rotation = np.arctan2(T_2d[1, 0], T_2d[0, 0])
        scale_x = T_2d[0, 0] / np.cos(rotation)
        scale_y = T_2d[1, 1] / np.cos(rotation)
        translation_x = T_2d[1, 2]
        translation_y = T_2d[0, 2]
        
        rotate_T = np.eye(4)
        rotate_T[1, 1] = np.cos(rotation)
        rotate_T[1, 2] = np.sin(rotation)
        rotate_T[2, 1] = -np.sin(rotation)
        rotate_T[2, 2] = np.cos(rotation)
        
        scale_T = np.eye(4)
        scale_T[1, 1] = scale_y
        scale_T[2, 2] = scale_x
        
        translate_T = np.eye(4)
        translate_T[2, 3] = translation_x
        translate_T[1, 3] = translation_y

        T = np.matmul(scale_T, T)
        T = np.matmul(rotate_T, T)
        T = np.matmul(translate_T, T)
    
    return T
