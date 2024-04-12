import os
import dask.array as da
from dask import delayed
import time
from tifffile import imread, TiffFile, xml2dict
from napari.qt import thread_worker
from skimage.io.collection import alphanumeric_key

from napari_sbem_viewer.utils import get_ome_pixel_size


class LiveViewer():
    def __init__(self, napari_viewer, layer_name='EM overview'):
        self.viewer = napari_viewer
        self.watching = False
        self.time_interval = 1
        self.processed_files = set()
        self.files_to_process = []
        self.running = False
        self.image_dir = None
        self.image_shape = None
        self.pixel_size_x = None
        self.pixel_size_y = None
        self.pixel_size_z = None
        self.layer_name = layer_name
        
    def init_metadata(self, image_file):
        with TiffFile(image_file) as tiff:
            tiff = TiffFile(image_file)
            xml_metadata = tiff.ome_metadata
            if xml_metadata is None:
                raise ValueError("File does not contain OME metadata.")
            if self.image_shape is None:
                self.image_shape = tiff.pages[0].shape
            else:
                if self.image_shape != tiff.pages[0].shape:
                    raise ValueError("All images must have same shape.")
            metadata_dict = xml2dict(xml_metadata)
            self.pixel_size_x = get_ome_pixel_size(metadata_dict, 'X')
            self.pixel_size_y = get_ome_pixel_size(metadata_dict, 'Y')
        tiff.close()
        
    @property
    def image_layer(self):
        return self._get_layer()
        
    def init_images(self, image_dir):
        self.reset()
        # add the existing images to the viewer
        self.image_dir = image_dir
        if os.path.exists(image_dir):
            for image in sorted(os.listdir(image_dir)):
                if image.endswith('.tif') or image.endswith('.tiff'):
                    self.init_metadata(os.path.join(image_dir, image))
                    self.append(delayed(imread)(os.path.join(image_dir, image)))
                    self.processed_files.add(image)
        
    def append(self, delayed_image):
        if delayed_image is None:
            return
        # wait a short time until the image is written to disk
        time.sleep(0.1)
        if layer:= self._get_layer():
            shape = layer.data.shape[1:]
            dtype = layer.data.dtype
            image = da.from_delayed(
                delayed_image, shape=shape, dtype=dtype
            ).reshape((1,) + shape)
            self._append_to_layer(image)
        else:
            image = delayed_image.compute()
            image = da.from_delayed(
                delayed_image, shape=image.shape, dtype=image.dtype,
            ).reshape((1,) + image.shape)
            layer = self._create_layer(image)

        if self.viewer.dims.current_step[0] >= layer.data.shape[0] - 2:
            self.viewer.dims.set_point(0, layer.data.shape[0] - 1)
            
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
        return layer.data_to_world((layer.data.shape[0] - 1, 0, 0))[0]
        
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
                
            # yield every file to process as a dask.delayed function object.
            for p in sorted(files_to_process, key=alphanumeric_key):
                self.init_metadata(os.path.join(path, p))
                yield delayed(imread)(os.path.join(path, p))
            else:
                yield

            # add the files which we have yield to the processed list.
            self.processed_files.update(files_to_process)
            time.sleep(self.time_interval)

        # _watch_folder()

    def stop_watching(self):
        self.watching = False
    
    def reset(self):
        self.processed_files = set()
        self.files_to_process = []
        self.image_shape = None
        self.pixel_size = None
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
        
        self.viewer.add_image(image, rendering='attenuated_mip', name=self.layer_name, scale=scale)
        return self.image_layer
    
    def _append_to_layer(self, image):
        layer = self.viewer.layers[self.layer_name]
        layer.data = da.concatenate((layer.data, image), axis=0)
        
    def _get_layer(self):
        for layer in self.viewer.layers:
            if layer.name == self.layer_name:
                return layer
        return None
    
    def _remove_layer(self):
        if layer := self.image_layer:
            self.viewer.layers.remove(layer)