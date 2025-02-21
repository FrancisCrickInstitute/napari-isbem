from qtpy.QtCore import QObject, Signal
import tifffile
from napari_ome_zarr import napari_get_reader
from napari.layers import Layer, Labels
import numpy as np


class LayerModel(QObject):
    targeting_layer_added = Signal(object)
    targeting_layer_removed = Signal()
    em_layer_added = Signal(object)
    em_layer_removed = Signal()
    labels_layer_added = Signal(object)
    labels_layer_removed = Signal()
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.targeting_layer = None
        self.em_layer = None
        self.labels_layer = None
        self.viewer.layers.events.removed.connect(self._on_remove_layer)
        
    def import_targeting_image(self, file_path):
        if not file_path.endswith('.ome.zarr'):
            raise ValueError("Invalid file format. Must be an OME-Zarr file.")
        reader = napari_get_reader(file_path)
        layer = Layer.create(*reader(file_path)[0])
        layer.contrast_limits = (0, 65535)
        self.add_targeting_layer(layer)
        
    def add_targeting_layer(self, layer):
        self.targeting_layer = layer
        self.viewer.add_layer(layer)
        self.targeting_layer_added.emit(layer)
        
    def remove_targeting_layer(self):
        self._remove_layer(self.targeting_layer)
        self.targeting_layer = None
        self.targeting_layer_removed.emit()
        
    def add_em_layer(self, layer):
        self.em_layer = layer
        self.viewer.add_layer(layer)
        self.em_layer_added.emit(layer)
    
    def remove_em_layer(self):
        self._remove_layer(self.em_layer)
        self.em_layer = None
        self.em_layer_removed.emit()
        
    def add_new_labels_layer(self, downsample_factor):
        labels_shape = [dim // downsample_factor for dim in self.targeting_layer.data.shape]
        labels = np.zeros(labels_shape, dtype=np.uint8)
        layer = Labels(
            labels,
            name="ROIs",
            scale=[downsample_factor * s for s in self.targeting_layer.scale],
            )
        self.add_labels_layer(layer)
        
    def upload_existing_labels(self, file_path):
        labels = tifffile.imread(file_path)
        scale_factors = calculate_scale(labels.shape, self.targeting_layer.data.shape)
        scale = [s * f for s, f in zip(self.targeting_layer.scale, scale_factors)]
        layer = Labels(labels, name="ROIs", scale=scale)
        self.add_labels_layer(layer)
    
    def add_labels_layer(self, layer):
        self.labels_layer = layer
        self.viewer.add_layer(layer)
        self.labels_layer_added.emit(layer)
        
    def remove_labels_layer(self):
        self._remove_layer(self.labels_layer)
        self.labels_layer = None
        self.labels_layer_removed.emit()
        
    def export_labels(self, file_path):
        if self.labels_layer is None:
            raise ValueError("No labels layer found")
        tifffile.imsave(file_path, self.labels_layer.data)
        
    def _remove_layer(self, layer):
        if layer in self.viewer.layers:
            self.viewer.layers.remove(layer)
        
    def _on_remove_layer(self, event):
        if event.value == self.targeting_layer:
            self.remove_labels_layer()
            self.targeting_layer = None
            self.targeting_layer_removed.emit()
        elif event.value == self.em_layer:
            self.em_layer = None
            self.em_layer_removed.emit()
        elif event.value == self.labels_layer:
            self.labels_layer = None
            self.labels_layer_removed.emit()
        
        
def calculate_scale(source_shape, target_shape):
    return [dim1 / dim2 for dim1, dim2 in zip(target_shape, source_shape)]
