import os
import warnings

import numpy as np
from qtpy.QtWidgets import QErrorMessage
import math
import psutil
import napari


def display_qt_error(parent, error):
        """Handle when an error occurs

        Show the error in an error message window.
        """
        em = QErrorMessage(parent)
        em.showMessage(str(error))
        
        
def is_multiple(a, b):
    """
    Returns True if b is a multiple of a, False otherwise.
    """
    ratio = a / b
    return math.isclose(ratio, round(ratio))


def log_memory_usage():
    process = psutil.Process(os.getpid())
    print(f"Memory usage: {process.memory_info().rss / 1024 ** 2} MB")


def log_memory_usage():
    process = psutil.Process(os.getpid())
    print(f"Memory usage: {process.memory_info().rss / 1024 ** 2} MB")
    
    
def reset_view(viewer: napari.Viewer, layer: napari.layers.Layer):
    if viewer.dims.ndisplay != 2:
        return
    if len(viewer.dims.displayed) == layer.extent.world.shape[1]:
        extent = layer.extent.world
    else:
        extent = layer.extent.world[:, viewer.dims.displayed]
    size = extent[1] - extent[0]
    center = extent[0] + size/2
    viewer.camera.center = center
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        canvas_size = viewer._canvas_size
    viewer.camera.zoom = np.min(canvas_size) / np.max(size)


def get_roi_center(coords_list):
    # calculate the min / max values of the x, y and z coordinates
    min_coords = np.min(coords_list, axis=0)
    max_coords = np.max(coords_list, axis=0)
    center_coords = (min_coords + max_coords) / 2
    return center_coords


def round_up_to_odd(f):
    return int(np.ceil(f) // 2 * 2 + 1)
