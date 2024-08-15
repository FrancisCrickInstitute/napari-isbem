"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/stable/plugins/guides.html?#readers
"""
from functools import partial

from tifffile import TIFF
from napari_tiff.napari_tiff_reader import reader_function
from skimage import measure
from qtpy.QtWidgets import QDialog, QComboBox, QVBoxLayout, QLabel, QDialogButtonBox
from napari._qt.qt_resources import get_stylesheet

from napari_sbem_viewer._utils.image_utils import downsample_3d_image_sitk


DOWNSAMPLE_FACTORS = {
    'None': None,
    '2x': 2,
    '4x': 4,
    '8x': 8
}


def get_labels_reader(path):
    """A basic implementation of a Reader contribution.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    function or None
        If the path is a recognized format, return a function that accepts the
        same path or list of paths, and returns a list of layer data tuples.
    """
    if isinstance(path, list):
        # reader plugins may be handed single path, or a list of paths.
        # if it is a list, it is assumed to be an image stack...
        # so we are only going to look at the first file.
        path = path[0]
    path = path.lower()
    for ext in TIFF.FILE_EXTENSIONS:
        dialog = DownsamplePopupWindow()
        result = dialog.exec_()
        if result != QDialog.Accepted:
            return
        downsample_factor = DOWNSAMPLE_FACTORS[dialog.combo_box.currentText()]
        if path.endswith(ext):
            return partial(labels_reader, downsample_factor=downsample_factor)
    return None


def labels_reader(path, downsample_factor=None):
    """Take a path or list of paths and return a list of LayerData tuples.

    Readers are expected to return data as a list of tuples, where each tuple
    is (data, [add_kwargs, [layer_type]]), "add_kwargs" and "layer_type" are
    both optional.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    layer_data : list of tuples
        A list of LayerData tuples where each tuple in the list contains
        (data, metadata, layer_type), where data is a numpy array, metadata is
        a dict of keyword arguments for the corresponding viewer.add_* method
        in napari, and layer_type is a lower-case string naming the type of
        layer. Both "meta", and "layer_type" are optional. napari will
        default to layer_type=="image" if not provided
    """
    data, metadata_kwargs, _ = reader_function(path)[0]
    del metadata_kwargs['blending']
    del metadata_kwargs['channel_axis']
    del metadata_kwargs['colormap']
    del metadata_kwargs['contrast_limits']
    del metadata_kwargs['rgb']

    if downsample_factor is not None:
        data = downsample_3d_image_sitk(data, downsample_factor)
        if 'scale' in metadata_kwargs:
            metadata_kwargs['scale'] = tuple([s * downsample_factor for s in metadata_kwargs['scale']])
        
    data = measure.label(data)
    return [(data, metadata_kwargs, 'labels')]
    
    
class DownsamplePopupWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(get_stylesheet("dark"))

        # Set up the combo box with some example options
        self.combo_box = QComboBox()
        self.combo_box.addItems(DOWNSAMPLE_FACTORS.keys())

        # Add a label to instruct the user
        label = QLabel("Downsample factor:")

        # Dialog buttons (OK and Cancel)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)  # OK button
        button_box.rejected.connect(self.reject)  # Cancel button

        # Set up the layout for the dialog
        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.combo_box)
        layout.addWidget(button_box)
        self.setLayout(layout)
        