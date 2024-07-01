import os
import time

import dask.array as da
from dask import delayed
from tifffile import imread, TiffFile, xml2dict
from skimage.io.collection import alphanumeric_key
import numpy as np

from napari_sbem_viewer._utils.image_utils import get_ome_pixel_size, load_as_dask


class LiveViewer():
    def __init__(self, napari_viewer, layer_name='EM overview'):
        self.viewer = napari_viewer
        self.watching = False
        self.time_interval = 1
        self.processed_files = set()
        self.files_to_process = []
        self.running = False
        self.image_dir = None
        self.image_shapes = []
        self.pixel_size_x = None
        self.pixel_size_y = None
        self.pixel_size_z = None
        self.dtype = None
        self.layer_name = layer_name
        
    def init_metadata(self, tiff):
        xml_metadata = tiff.ome_metadata
        if xml_metadata is not None:
            metadata_dict = xml2dict(xml_metadata)
            self.pixel_size_x = get_ome_pixel_size(metadata_dict, 'X')
            self.pixel_size_y = get_ome_pixel_size(metadata_dict, 'Y')
        else:
            self.pixel_size_x = 1
            self.pixel_size_y = 1
            # raise ValueError("File does not contain OME metadata.")
        if not self.image_shapes:
            for page in tiff.pages:
                self.image_shapes.append(page.shape)
        else:
            if len(self.image_shapes) != len(tiff.pages):
                raise ValueError("All images must have same number of pages.")
            for shape, page in zip(self.image_shapes, tiff.pages):
                if shape != page.shape:
                    raise ValueError("All images must have same shape.")
        if self.dtype is None:
            self.dtype = tiff.pages[0].asarray().dtype
        
    @property
    def image_layer(self):
        return self._get_layer()
        
    def init_images(self, image_dir):
        # add the existing images to the viewer
        self.image_dir = image_dir
        dask_arrays = []
        if os.path.exists(image_dir):
            for image in sorted(os.listdir(image_dir)):
                if image.endswith('.tif') or image.endswith('.tiff'):
                    tiff = TiffFile(os.path.join(image_dir, image))
                    self.init_metadata(tiff)
                    image_pyramids = load_as_dask(tiff, self.dtype)
                    dask_arrays.append(image_pyramids)
                    self.processed_files.add(image)
                    
        dask_arrays_transposed = list(zip(*dask_arrays))
        stack = [da.stack(slices, axis=0) for slices in dask_arrays_transposed]
        if stack:
            self._create_layer(stack)
        
    def append(self, tiff):
        if tiff is None:
            return
        image_pyramids = load_as_dask(tiff, self.dtype)
        
        if layer:= self._get_layer():
            self._append_to_layer(image_pyramids)
        else:
            layer = self._create_layer([image[np.newaxis, :, :] for image in image_pyramids])
            
        latest_z_value_um = self.image_layer.data_to_world((layer.data.shape[0] - 1, 0, 0))[0]
        self.viewer.dims.set_point(0, latest_z_value_um)
            
    def wait_for_image(self):
        if self.image_dir is None:
            raise ValueError("Image directory is not set.")
        self.running = True
        while self.running and not len(self.files_to_process):
            if os.path.exists(self.image_dir):
                for filename in sorted(os.listdir(self.image_dir), reverse=True):
                    if filename.endswith('.tif') or filename.endswith('.tiff'):
                        if filename not in self.processed_files:
                            self.files_to_process.append(filename)
            time.sleep(self.time_interval)
        self.running = False
                
        if len(self.files_to_process):
            filename = self.files_to_process.pop()
            self.processed_files.add(filename)
            return delayed(imread)(os.path.join(self.image_dir, filename))
        
    def get_current_z_depth(self):
        layer = self.image_layer
        if layer is None:
            return None
        return layer.data_to_world((layer.data.shape[0], 0, 0))[0]
        
    def watch_folder(self, path):
        self.watching = True
        current_files = set()
        while self.watching:
            files_to_process = set()
            # Get the all files in the directory at this time
            current_files = set()
            for file in os.listdir(path):
                if file.endswith('.tif') or file.endswith('.tiff'):
                    current_files.add(file)

            if len(current_files):
                files_to_process = current_files - self.processed_files
                
            # add an extra delay to ensure the image is correctly written to disk before processing
            if files_to_process:
                time.sleep(self.time_interval)
            # yield every tiff file after checking the metadata is correct
            for p in sorted(files_to_process, key=alphanumeric_key):
                tiff = TiffFile(os.path.join(path, p))
                self.init_metadata(tiff)
                yield tiff
            else:
                yield

            # add the files which we have yield to the processed list.
            self.processed_files.update(files_to_process)
            time.sleep(self.time_interval)

    def stop_watching(self):
        self.watching = False
    
    def reset(self):
        self.processed_files = set()
        self.files_to_process = []
        self.image_shapes = []
        self.pixel_size_x = None
        self.pixel_size_y = None
        self.dtype = None
        self.res_unit = None
        self.image_dir = None
        self.watching = False
        self._remove_layer()
        
    def _remove_layer(self):
        if layer:= self.image_layer:
            self.viewer.layers.remove(layer)
    
    def _create_layer(self, image):
        if self.pixel_size_z is None:
            raise ValueError("Pixel size in z is not set.")
        if self.pixel_size_x is not None and self.pixel_size_y is not None:
            scale = (self.pixel_size_z, self.pixel_size_y, self.pixel_size_x)
        else:
            scale = (self.pixel_size_z, 1, 1)
        self.viewer.add_image(image, rendering='attenuated_mip', name=self.layer_name, scale=scale, multiscale=True)
        return self.image_layer
    
    def _append_to_layer(self, image_pyramid):
        layer = self.viewer.layers[self.layer_name]
        layer.data = [da.concatenate([layer.data[i], image_pyramid[i][np.newaxis]], axis=0) for i in range(len(image_pyramid))]
        
    def _get_layer(self):
        for layer in self.viewer.layers:
            if layer.name == self.layer_name:
                return layer
        return None
    
    def _remove_layer(self):
        if layer := self.image_layer:
            self.viewer.layers.remove(layer)