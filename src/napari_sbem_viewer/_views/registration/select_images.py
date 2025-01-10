import napari
from napari.layers import Image, Labels
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox, QLabel


class SelectImages(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__("Select images", parent=parent)
        self.viewer = viewer
        self.setLayout(QVBoxLayout())
        
        self.fixed_combo_box = QComboBox()
        self.moving_combo_box = QComboBox()
        
        fixed_lyt = QHBoxLayout()
        fixed_lyt.addWidget(QLabel("Fixed"))
        fixed_lyt.addWidget(self.fixed_combo_box, 1)
        self.layout().addLayout(fixed_lyt)
        
        moving_lyt = QHBoxLayout()
        moving_lyt.addWidget(QLabel("Moving"))
        moving_lyt.addWidget(self.moving_combo_box, 1)
        self.layout().addLayout(moving_lyt)
        
        self.viewer.layers.events.removed.connect(self._on_remove_layer)
        self.viewer.layers.events.inserted.connect(self._on_add_layer)
        self._populate_combo_boxes()
        
    def get_moving_layer(self):
        return self._get_layer(self.moving_combo_box.currentText())
    
    def get_fixed_layer(self):
        return self._get_layer(self.fixed_combo_box.currentText())
    
    def _populate_combo_boxes(self):
        for layer in self.viewer.layers:
            if isinstance(layer, Image) or isinstance(layer, Labels):
                self.fixed_combo_box.addItem(layer.name)
                self.moving_combo_box.addItem(layer.name)
                
    def _on_add_layer(self, event):
        if not (isinstance(event.value, Image) or isinstance(event.value, Labels)):
            return
        self.fixed_combo_box.addItem(event.value.name)
        self.moving_combo_box.addItem(event.value.name)
        
    def _on_remove_layer(self, event):
        if isinstance(event.value, Image) or isinstance(event.value, Labels):
            idx = self.fixed_combo_box.findText(event.value.name)
            if idx >= 0:
                self.fixed_combo_box.removeItem(idx)
            idx = self.moving_combo_box.findText(event.value.name)
            if idx >= 0:
                self.moving_combo_box.removeItem(idx)
        
    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
        