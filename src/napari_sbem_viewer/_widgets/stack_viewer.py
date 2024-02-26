import napari
from napari.qt import QtViewer
from napari.layers.points._points_constants import Mode
from qtpy.QtCore import Qt

from copy import copy


class StackViewer(QtViewer):
    def __init__(self, viewer: napari.Viewer, points_layer_config=None, parent=None):
        super().__init__(viewer)
        if parent is not None:
            self.setParent(parent)
        self.viewer = viewer
        self.points_layer_name = 'points'
        self.points_layer_config = points_layer_config
        self.points_layer = None
        self.substack_layer = None
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
        
    def view_substack(self, image_layer, center_coords, image_width=20):
        center_coords_scaled = image_layer.world_to_data(center_coords)
        scale = image_layer.scale
        scale = [0.325, 0.325, 0.325]  # TODO: remove when correct metadata is available
        
        # select a crop around the center coords
        image_crop = image_layer.data[
            int(max(0, center_coords_scaled[0] - image_width / scale[0])):int(min(center_coords_scaled[0] + image_width / scale[0], image_layer.data.shape[0])),
            int(max(0, center_coords_scaled[1] - image_width / scale[1])):int(min(center_coords_scaled[1] + image_width / scale[1], image_layer.data.shape[1])),
            int(max(0, center_coords_scaled[2] - image_width / scale[2])):int(min(center_coords_scaled[2] + image_width / scale[2], image_layer.data.shape[2])),
        ]
        if self.substack_layer is None:
            self.substack_layer = self.viewer.add_image(image_crop, name='substack', scale=scale)
            self.substack_layer.mouse_pan = False
            self.substack_layer.mouse_zoom = False
        else:
            self.substack_layer.data = image_crop
            self.substack_layer.scale = image_layer.scale
        
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
            
    def remove_substack(self):
        if self.substack_layer is not None:
            self.viewer.layers.remove(self.substack_layer)
            self.substack_layer = None
        
    def _on_change_points_layer_name(self, event):
        self.points_layer_name = event.value
        
    def _on_change_layer_name(self, event):
        self.points_layer_name = self.viewer.layers[event.index].name