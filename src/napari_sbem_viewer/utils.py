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
    print(a, b)
    ratio = a / b
    print(ratio)
    return math.isclose(ratio, round(ratio))


def load_as_dask(tiff):
    arrays = []
    for level in range(len(tiff.pages)):
        data = da.from_zarr(tiff.aszarr(level=level))
        if data.chunksize == data.shape:
            data = data.rechunk()
        arrays.append(data)
    return arrays


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