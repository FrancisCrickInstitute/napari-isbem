import os
import time
import math

import dask.array as da
from tifffile import TiffFile, xml2dict
from skimage.io.collection import alphanumeric_key
import numpy as np

from napari_sbem_viewer._utils.image_utils import get_ome_pixel_size, get_ome_position, load_as_dask


class LiveViewer():
    def __init__(self, napari_viewer, layer_name):
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
        return len(self.added_files) > 1
    
    def init_images(self, image_dir):
        """
        Initializes the images in image_dir and creates an image layer in the napari viewer.
        """
        if not os.path.exists(image_dir):
            self.reset()
            raise ValueError("Image directory does not exist.")
        self.image_dir = image_dir
        dask_arrays = []
        for tiff in self._get_images_from_dir():
            image_pyramids = load_as_dask(tiff, self.dtype)
            dask_arrays.append(image_pyramids)
                
        if len(self.added_files) < 2:
            self.reset()
            raise ValueError("Image directory must contain at least 2 images.")
                    
        dask_arrays_transposed = list(zip(*dask_arrays))
        stack = [da.stack(slices, axis=0) for slices in dask_arrays_transposed]
        self.layer = self._create_layer(stack)
            
    def watch(self):
        """
        Repeatedly watches image_dir and yields tiffs that should be added to the viewer.
        """
        if self.image_dir is None:
            raise ValueError("Initialize image_dir before watching.")
        
        self.watching = True
        while self.watching:
            # yield every tiff file after checking the metadata is correct
            for tiff in self._get_images_from_dir():
                yield tiff
                    
    def append(self, tiff):
        if self.layer is None:
            raise ValueError("Image layer not initialized.")

        image_pyramids = load_as_dask(tiff, self.dtype)
        self._append_to_layer(image_pyramids)
        latest_z_value_um = self.layer.data_to_world((self.layer.data.shape[0] - 1, 0, 0))[0]
        self.viewer.dims.set_point(0, latest_z_value_um)
        
    def get_current_z_depth(self):
        if self.layer is None:
            return None
        return self.layer.data_to_world((self.layer.data.shape[0], 0, 0))[0]
    
    def reset(self):
        self.watching = False
        # Wait until the worker thread has finished processing the current loop
        time.sleep(self.time_interval)  # TODO: look into this: might be better to kill worker thread instead
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
        self._remove_layer()
        
    def _get_images_from_dir(self):
        """
        Searches all unprocessed files in image_dir and yields tiffs that
        should be added to the viewer.
        """
        assert self.image_dir is not None  # Ensure image_dir has been initialized
        
        sorted_files = sorted(os.listdir(self.image_dir), key=alphanumeric_key)
        time.sleep(self.time_interval)  # Ensure files are properly written before processing

        # yield every tiff file after checking the metadata is correct
        for filename in sorted_files:
            if filename.endswith('.tif') or filename.endswith('.tiff') or not filename.startswith('grab'):
                tiff = TiffFile(os.path.join(self.image_dir, filename))
                if (filename not in self.added_files) and (filename not in self.skipped_files):
                    if self._init_metadata(tiff):
                        self.added_files.add(filename)
                        yield tiff
                else:
                    self.skipped_files.add(filename)
        
    def _init_metadata(self, tiff):
        # Get ome metadata from tiff
        xml_metadata = tiff.ome_metadata
        if xml_metadata is None:
            raise ValueError("File does not contain OME metadata.")
        metadata_dict = xml2dict(xml_metadata)
        
        if not self.image_shapes:
            # Get pyramid sizes from ome-tiff
            for page in tiff.pages:
                self.image_shapes.append(page.shape)
        else:
            # Check if current image sizes match initial sizes
            if len(self.image_shapes) != len(tiff.pages):
                raise ValueError("All images must have same number of pages.")
            for shape, page in zip(self.image_shapes, tiff.pages):
                if shape != page.shape:
                    raise ValueError("All images must have same shape.")

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
            self.pixel_size_z = round(get_ome_position(metadata_dict, 'Z') - self.position_z, 5)
            return True
        
        # For subsequent images, check if the current z depth matches expected values
        current_z = get_ome_position(metadata_dict, 'Z')
        return self._check_z_depth(current_z)

    def _check_z_depth(self, current_z):
        assert self.pixel_size_z is not None
        expected_z = self.position_z + self.pixel_size_z * len(self.added_files)
        # Add image to the viewer if current z depth matches expected value
        if math.isclose(expected_z, current_z):
            return True
        # Don't add image to the viewer if the current z depth is too small
        elif current_z < expected_z:
            return False
        # Raise an error if the current z depth is too large
        else:
            raise ValueError(f"Inconsitent Z spacing between images. Expected: {expected_z:.2f}, Got: {current_z:.2f}")  
    
    def _create_layer(self, image):
        if self.pixel_size_z is None:
            raise ValueError("Pixel size in z is not set.")
        if self.pixel_size_x is not None and self.pixel_size_y is not None:
            scale = (self.pixel_size_z, self.pixel_size_y, self.pixel_size_x)
        else:
            scale = (self.pixel_size_z, 1, 1)
        layer = self.viewer.add_image(
            image, 
            rendering='attenuated_mip', 
            name=self.layer_name, 
            scale=scale, 
            multiscale=True)
        return layer
    
    def _get_size_um(self):
        return (self.image_shapes[0][0] * self.pixel_size_y, self.image_shapes[0][1] * self.pixel_size_x)
    
    def _append_to_layer(self, image_pyramid):
        layer = self.viewer.layers[self.layer_name]
        layer.data = [da.concatenate([layer.data[i], image_pyramid[i][np.newaxis]], axis=0) 
                      for i in range(len(image_pyramid))]
    
    def _remove_layer(self):
        try:
            self.viewer.layers.remove(self.layer)
        except Exception:
            pass
        self.layer = None
            