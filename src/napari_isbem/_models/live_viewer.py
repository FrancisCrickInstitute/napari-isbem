import math
import os
import time

import dask.array as da
import numpy as np
from napari.layers import Image
from napari.qt import create_worker
from qtpy.QtCore import QObject, Signal
from skimage.io.collection import alphanumeric_key
from tifffile import TiffFile, xml2dict
from tqdm import tqdm

from napari_isbem._utils.image_utils import (
    get_ome_pixel_size,
    get_ome_position,
    load_as_dask,
)


class LiveViewerNotInitializedError(Exception):
    """Exception raised when the LiveViewer is not initialized.

    This error is raised when an attempt is made to process an acquisition request
    without the LiveViewer being properly initialized.
    """


class LiveViewer(QObject):
    """Live image stack manager for viewing 3D stacks during acquisition.

    The LiveViewer class manages the loading of 2D image stacks into a 3D image layer
    in a napari viewer. It supports watching a directory for new images, appending
    new images to the layer. It also handles metadata parsing from OME-TIFF files.

    Attributes:
        initialized (Signal): Emitted when the image layer is initialized.
        cleared (Signal): Emitted when the viewer is reset.
        errored (Signal): Emitted when an error occurs, with a title and message.
        viewer: The napari viewer instance.
        layer_name (str): Name for the image layer.
        layer: The napari Image layer managed by this viewer.
        pixel_size_x, pixel_size_y, pixel_size_z: Physical pixel sizes.
        position_x, position_y, position_z: Physical position of the stack origin.
        size_x, size_y: Physical size of the image in x and y.
        dtype: Data type of the image.
        watching (bool): Whether the viewer is actively watching for new images.
    """

    initialized = Signal(object)
    cleared = Signal()
    errored = Signal(str, str)

    def __init__(self, napari_viewer, layer_name):
        """Initializes the LiveViewer.

        Args:
            napari_viewer: The napari viewer instance.
            layer_name (str): The name for the image layer.
        """
        super().__init__()
        self.viewer = napari_viewer
        self.watching = False
        self.time_interval = 1
        self.added_files = set()
        self.skipped_files = set()
        self.image_dir = None
        self.image_shapes = []
        self.pixel_size_x = None
        self.pixel_size_y = None
        self.pixel_size_z = None
        self.position_x = 0
        self.position_y = 0
        self.position_z = 0
        self.size_x = 0
        self.size_y = 0
        self.dtype = None
        self.layer_name = layer_name
        self.layer = None

    def is_initialized(self):
        """Checks if the LiveViewer has been initialized.

        Returns:
            bool: True if images have been added to the viewer, False otherwise.
        """
        return len(self.added_files) > 1

    def init_images(self, image_dir):
        """Initializes the images in the specified directory and creates an image layer.
        Emits the initialized signal with the created layer.

        Args:
            image_dir (str): Path to the directory containing image files.

        Raises:
            ValueError: If the directory does not exist or contains fewer than 2 images.
        """
        if not os.path.exists(image_dir):
            self.reset()
            raise FileNotFoundError('Image directory does not exist.')
        self.image_dir = image_dir
        dask_arrays = []
        for filename in tqdm(self._get_images_from_dir()):
            image_pyramids = load_as_dask(
                os.path.join(self.image_dir, filename),
                self.image_shapes,
                self.dtype,
            )
            dask_arrays.append(image_pyramids)

        if len(self.added_files) < 2:
            self.reset()
            raise ValueError('Image directory must contain at least 2 images.')

        dask_arrays_transposed = list(zip(*dask_arrays))
        stack = [da.stack(slices, axis=0) for slices in dask_arrays_transposed]
        self.layer = self._create_layer(stack)
        self.initialized.emit(self.layer)

    def start_watching(self, ov_dir):
        """Starts watching the specified directory for new images and initializes the viewer.

        Args:
            ov_dir (str): Path to the directory to watch.
        """
        self.reset()
        self.init_images(ov_dir)
        create_worker(
            self.watch,
            _connect={'yielded': self.append, 'errored': self._handle_error},
        )

    def watch(self):
        """Watches the image directory for new TIFF files and yields them for processing.

        Yields:
            TiffFile: TIFF files to be added to the viewer.

        Raises:
            ValueError: If image_dir is not initialized.
        """
        if self.image_dir is None:
            raise ValueError('Initialize image_dir before watching.')

        self.watching = True
        while self.watching:
            # yield every tiff filename after checking the metadata is correct
            yield from self._get_images_from_dir()

    def append(self, filename):
        """Appends a new TIFF image to the current image layer.

        Args:
            filename (str): The filename of the TIFF to append to the viewer.

        Raises:
            ValueError: If the image layer is not initialized.
        """
        if self.layer is None:
            raise ValueError('Image layer not initialized.')

        image_pyramids = load_as_dask(
            os.path.join(self.image_dir, filename),
            self.image_shapes,
            self.dtype,
        )
        self._append_to_layer(image_pyramids)
        self.reset_z_view()

    def reset_z_view(self):
        """Resets the viewer to show the latest z-slice."""
        if self.layer is None:
            return
        latest_z_value_um = self.layer.data_to_world(
            (self.layer.data.shape[0] - 1, 0, 0)
        )[0]
        self.viewer.dims.set_point(0, latest_z_value_um)

    def get_current_z_depth(self):
        """Gets the current z-depth in world coordinates.

        Returns:
            float or None: The current z-depth, or None if the layer is not initialized.
        """
        if self.layer is None:
            return None
        return self.layer.data_to_world((self.layer.data.shape[0], 0, 0))[0]

    def reset(self):
        """Resets the LiveViewer state and emits the cleared signal."""
        self.watching = False
        # Wait until the worker thread has finished processing the current loop
        time.sleep(
            self.time_interval
        )  # TODO: look into this: might be better to kill worker thread instead
        self.added_files = set()
        self.skipped_files = set()
        self.image_shapes = []
        self.pixel_size_x = None
        self.pixel_size_y = None
        self.pixel_size_z = None
        self.position_x = 0
        self.position_y = 0
        self.position_z = 0
        self.size_x = 0
        self.size_y = 0
        self.dtype = None
        self.res_unit = None
        self.image_dir = None
        self.cleared.emit()

    def _get_images_from_dir(self):
        """
        Searches all unprocessed files in image_dir and yields tiffs that
        should be added to the viewer.
        """
        assert (
            self.image_dir is not None
        )  # Ensure image_dir has been initialized

        sorted_files = sorted(os.listdir(self.image_dir), key=alphanumeric_key)
        time.sleep(
            self.time_interval
        )  # Ensure files are properly written before processing

        # yield every tiff file after checking the metadata is correct
        for filename in sorted_files:
            if not filename.endswith('.tif') and not filename.endswith(
                '.tiff'
            ):
                continue
            if filename.startswith('grab'):
                continue
            if (filename not in self.added_files) and (
                filename not in self.skipped_files
            ):
                with TiffFile(os.path.join(self.image_dir, filename)) as tiff:
                    if self._init_metadata(tiff):
                        self.added_files.add(filename)
                        yield filename
                    else:
                        self.skipped_files.add(filename)

    def _init_metadata(self, tiff):
        """Initializes metadata from the TIFF file and checks validity.

        If this is the first image, sets metadata attributes. For subsequent images,
        checks that metadata is consistent with the initial image.

        Args:
            tiff (TiffFile): The TIFF file to extract metadata from.

        Returns:
            bool: True if the image should be added to the viewer, False if it should be skipped.

        Raises:
            ValueError: If the file does not contain OME metadata, or if metadata is invalid or inconsistent.
        """
        # Get ome metadata from tiff
        xml_metadata = tiff.ome_metadata
        if xml_metadata is None:
            raise ValueError('File does not contain OME metadata.')
        metadata_dict = xml2dict(xml_metadata)

        if not self.image_shapes:
            # Get pyramid sizes from ome-tiff
            for page in tiff.pages:
                self.image_shapes.append(page.shape)
        else:
            # Check if current image sizes match initial sizes
            if len(self.image_shapes) != len(tiff.pages):
                raise ValueError('All images must have same number of pages.')
            for shape, page in zip(self.image_shapes, tiff.pages):
                if shape != page.shape:
                    raise ValueError('All images must have same shape.')

        # If processing the first image, obtain position and pixel size metadata
        # and add the image to the viewer
        if not len(self.added_files):
            self.pixel_size_x = get_ome_pixel_size(metadata_dict, 'X')
            self.pixel_size_y = get_ome_pixel_size(metadata_dict, 'Y')
            self.size_y, self.size_x = self._get_size_um()
            self.position_x = get_ome_position(metadata_dict, 'X')
            self.position_y = get_ome_position(metadata_dict, 'Y')
            self.position_z = get_ome_position(metadata_dict, 'Z')
            self.dtype = tiff.pages[0].asarray().dtype
            return True

        # If processing the second image, obtain the z pixel size metadata
        # and add the image to the viewer
        elif len(self.added_files) == 1:
            self.pixel_size_z = round(
                get_ome_position(metadata_dict, 'Z') - self.position_z, 5
            )
            return True

        # For subsequent images, check if the current z depth matches expected values
        current_z = get_ome_position(metadata_dict, 'Z')
        return self._check_z_depth(current_z)

    def _check_z_depth(self, current_z):
        assert self.pixel_size_z is not None
        expected_z = self.position_z + self.pixel_size_z * len(
            self.added_files
        )
        # Add image to the viewer if current z depth matches expected value
        # Allow for a tolerance of 0.0001 micrometers (0.1 nanometers)
        if math.isclose(expected_z, current_z, abs_tol=1e-4):
            return True
        # Don't add image to the viewer if the current z depth is too small
        elif current_z < expected_z:
            return False
        # Raise an error if the current z depth is too large
        else:
            raise ValueError(
                f'Inconsitent Z spacing between images. Expected: {expected_z:.2f}, Got: {current_z:.2f}'
            )

    def _create_layer(self, image):
        if self.pixel_size_z is None:
            raise ValueError('Pixel size in z is not set.')
        if self.pixel_size_x is not None and self.pixel_size_y is not None:
            scale = (self.pixel_size_z, self.pixel_size_y, self.pixel_size_x)
        else:
            scale = (self.pixel_size_z, 1, 1)
        layer = Image(
            image,
            rendering='attenuated_mip',
            name=self.layer_name,
            scale=scale,
            multiscale=True,
        )
        return layer

    def _get_size_um(self):
        return (
            self.image_shapes[0][0] * self.pixel_size_y,
            self.image_shapes[0][1] * self.pixel_size_x,
        )

    def _append_to_layer(self, image_pyramid):
        self.layer.data = [
            da.concatenate(
                [self.layer.data[i], image_pyramid[i][np.newaxis]], axis=0
            )
            for i in range(len(image_pyramid))
        ]

    def _handle_error(self, e):
        self.reset()
        self.errored.emit('Error adding images', str(e))
