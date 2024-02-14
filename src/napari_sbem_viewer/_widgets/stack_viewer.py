import napari
from napari.qt import QtViewer
from napari.layers.points._points_constants import Mode
from qtpy.QtCore import Qt

from copy import copy


class StackViewer(QtViewer):
    def __init__(self, viewer: napari.Viewer, points_layer_config, parent):
        super().__init__(viewer)
        self.setParent(parent)
        self.viewer = viewer
        self.points_layer_name = 'points'
        self.points_layer_config = points_layer_config
        self.points_layer = None
        self._image_layer = None
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        
    def clear(self):
        self.viewer.layers.clear()
    
    def add_points_layer(self):
        self.points_layer = self.viewer.add_points(name=self.points_layer_name, **self.points_layer_config)
        self.points_layer.events.name.connect(self._on_change_points_layer_name)
        
    def activate_points_layer(self):
        self.viewer.layers.selection.active = self.points_layer
        self.points_layer.mode = Mode.ADD
        
    @property
    def image_layer(self):
        return self._image_layer
        # self.image_layer.events.name.connect(self._on_change_layer_name)
        
    @image_layer.setter
    def image_layer(self, layer):
        self._image_layer = layer
        self.viewer.layers.clear()
        self.points_layer = None
        if layer is not None:
            self.viewer.layers.append(copy(layer))
    
    def _on_change_points_layer_name(self, event):
        self.points_layer_name = event.value
        
    def _on_change_layer_name(self, event):
        self.points_layer_name = self.stack_viewer.layers[event.index].name
        