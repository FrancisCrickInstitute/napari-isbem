from skimage.io.collection import alphanumeric_key
from napari.qt import thread_worker
import os
import dask.array as da
from dask import delayed
import time
from tifffile import imread
import socket
import json


class LiveViewer():
    def __init__(self, napari_viewer):
        self.viewer = napari_viewer
        self.watching = False
        self.time_interval = 1
        self.processed_files = set()
        
    def append(self, delayed_image):
        """Appends the image to viewer.

        Parameters
        ----------
        delayed_image : dask.delayed function object
        """
        if delayed_image is None:
            return

        if self.viewer.layers:
            # layer is present, append to its data
            layer = self.viewer.layers[0]
            image_shape = layer.data.shape[1:]
            image_dtype = layer.data.dtype
            image = da.from_delayed(
                delayed_image, shape=image_shape, dtype=image_dtype,
            ).reshape((1,) + image_shape)
            layer.data = da.concatenate((layer.data, image), axis=0)
        else:
            # first run, no layer added yet
            image = delayed_image.compute()
            image = da.from_delayed(
                delayed_image, shape=image.shape, dtype=image.dtype,
            ).reshape((1,) + image.shape)
            layer = self.viewer.add_image(image, rendering='attenuated_mip')

        # we want to show the last file added in the viewer to do so we want to
        # put the slider at the very end. But, sometimes when user is scrolling
        # through the previous slide then it is annoying to jump to last
        # stack as it gets added. To avoid that jump we 1st check where
        # the scroll is and if its not at the last slide then don't move the slider.
        if self.viewer.dims.point[0] >= layer.data.shape[0] - 2:
            self.viewer.dims.set_point(0, layer.data.shape[0] - 1)
            
    def watch_folder(self, path):
        # TODO: remove layer first if it exists and check for correct file paths and sizes
        # TODO: change name of layer to folder name
        # TODO: if folder is changed then clear processed files

        @thread_worker(connect={'yielded': self.append})
        def _watch_folder():
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
                    yield delayed(imread)(os.path.join(path, p))
                else:
                    yield

                # add the files which we have yield to the processed list.
                self.processed_files.update(files_to_process)
                time.sleep(self.time_interval)

        _watch_folder()
        self.watching = True

    def stop_watching(self):
        self.watching = False
        
        
class TCPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        
    def send(self, msg, *args, **kwargs):
        if self.host is None or self.port is None:
            raise ValueError("Host and port must be set before sending a message.")
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))

            command = {'msg': msg, 'args': args, 'kwargs': kwargs}

            s.sendall(json.dumps(command).encode('utf-8'))
            response = json.loads((s.recv(1024)))
            return response['response']
