from skimage.io.collection import alphanumeric_key
from napari.qt import thread_worker
import os
import dask.array as da
from dask import delayed
import time
from tifffile import imread, TiffFile, TiffWriter, xml2dict
import socket
import json
import cv2
import numpy as np
from qtpy.QtWidgets import QErrorMessage


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
            # self.pixel_size_x = convert_to_micrometers(
            #     tiff.pages[0].tags.get('PhysicalSizeX'),
            #     tiff.pages[0].tags.get('PhysicalSizeXUnits')
            # )
            # self.pixel_size_y = convert_to_micrometers(
            #     tiff.pages[0].tags.get('PhysicalSizeY'),
            #     tiff.pages[0].tags.get('PhysicalSizeYUnits')
            # )
        tiff.close()
        
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

    # def watch_folder(self, path):
        
    #     @thread_worker(connect={'yielded': self.append})
    #     def _watch_folder():
    #         current_files = set()
    #         while self.watching:
    #             files_to_process = set()
    #             # Get the all files in the directory at this time
    #             current_files = set()
    #             for file in os.listdir(path):
    #                 if file.endswith('.tif') or file.endswith('.tiff'):
    #                     current_files.add(file)

    #             if len(current_files):
    #                 files_to_process = current_files - self.processed_files
                    
    #             # yield every file to process as a dask.delayed function object.
    #             for p in sorted(files_to_process, key=alphanumeric_key):
    #                 self.init_metadata(os.path.join(path, p))
    #                 yield delayed(imread)(os.path.join(path, p))
    #             else:
    #                 yield

    #             # add the files which we have yield to the processed list.
    #             self.processed_files.update(files_to_process)
    #             time.sleep(self.time_interval)

    #     _watch_folder()
    #     self.watching = True

    # def stop_watching(self):
    #     self.watching = False
    
    def reset(self):
        self.processed_files = set()
        self.files_to_process = []
        self.image_shape = None
        self.pixel_size = None
        self.res_unit = None
        self.image_dir = None
        self._remove_layer()
        
    def _remove_layer(self):
        if layer := self._get_layer():
            self.viewer.layers.remove(layer)
    
    def _create_layer(self, image):
        if self.pixel_size_z is None:
            raise ValueError("Pixel size in z is not set.")
        if self.pixel_size_x is not None and self.pixel_size_y is not None:
            scale = (self.pixel_size_z, self.pixel_size_y, self.pixel_size_x)
        else:
            scale = (self.pixel_size_z, 1, 1)
        
        self.viewer.add_image(image, rendering='attenuated_mip', name=self.layer_name, scale=scale)
        return self._get_layer()
    
    def _append_to_layer(self, image):
        layer = self.viewer.layers[self.layer_name]
        layer.data = da.concatenate((layer.data, image), axis=0)
        
    def _get_layer(self):
        for layer in self.viewer.layers:
            if layer.name == self.layer_name:
                return layer
        return None
    
    def _remove_layer(self):
        if layer := self._get_layer():
            self.viewer.layers.remove(layer)
        
        
class TCPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        
    def start(self):
        return self.send('START')
        
    def pause(self):
        return self.send('PAUSE', 2)
    
    def get_z_depth(self):
        return self.send('GET Z DEPTH')
    
    def add_grid(self, x, y, w, h):
        return self.send('ADD GRID', x, y, w, h)
    
    def find_overview_dirs(self):
        return self.send('FIND OV DIRS')
    
    def get_overview_coords(self, ov_idx):
        return self.send('GET OV COORDS', ov_idx)
        
    def send(self, msg, *args, **kwargs):
        if self.host is None or self.port is None:
            raise ValueError("Host and port must be set before sending a message.")
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))

            command = {'msg': msg, 'args': args, 'kwargs': kwargs}

            s.sendall(json.dumps(command).encode('utf-8'))
            response = json.loads((s.recv(1024)))
            return response['response']


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
        