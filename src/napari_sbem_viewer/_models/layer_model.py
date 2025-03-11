from qtpy.QtCore import QObject, Signal
import tifffile
from napari_ome_zarr import napari_get_reader
from napari.layers import Layer


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
    
    def add_labels_layer(self, layer):
        self.labels_layer = layer
        self.viewer.add_layer(layer)
        self.labels_layer_added.emit(layer)
        
    def remove_labels_layer(self):
        self._remove_layer(self.labels_layer)
        self.labels_layer = None
        self.labels_layer_removed.emit()
        
    def export_labels_layer(self, file_path):
        if self.labels_layer is None:
            raise ValueError("No labels layer found")
        tifffile.imsave(file_path, self.labels_layer.data)
        
    def _remove_layer(self, layer):
        if layer in self.viewer.layers:
            self.viewer.layers.remove(layer)
        
    def _on_remove_layer(self, event):
        if event.value == self.targeting_layer:
            self.targeting_layer = None
            self.targeting_layer_removed.emit()
        elif event.value == self.em_layer:
            self.em_layer = None
            self.em_layer_removed.emit()
        elif event.value == self.labels_layer:
            self.labels_layer = None
            self.labels_layer_removed.emit()
