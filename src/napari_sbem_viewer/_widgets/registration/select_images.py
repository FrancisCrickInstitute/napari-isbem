import napari
from napari.layers.image.image import Image
from napari.layers.labels.labels import Labels
from qtpy.QtWidgets import QGridLayout, QGroupBox, QComboBox, QLabel


class SelectImages(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__("Select images", parent=parent)
        self.viewer = viewer
        self.setLayout(QGridLayout())
        
        self.layout().addWidget(QLabel("Fixed image"))
        self.fixed_combo_box = QComboBox()
        self.layout().addWidget(self.fixed_combo_box)
        
        self.layout().addWidget(QLabel("Moving stack"))
        self.moving_combo_box = QComboBox()
        self.layout().addWidget(self.moving_combo_box)
        
        self.viewer.layers.events.removed.connect(self._update_selections)
        self.viewer.layers.events.inserted.connect(self._update_selections)
        
        self._update_selections()
        
    def get_moving_layer(self):
        return self._get_layer(self.moving_combo_box.currentText())
    
    def get_fixed_layer(self):
        return self._get_layer(self.fixed_combo_box.currentText())
        
    def _update_selections(self):
        layer_names = self._get_image_layer_names()
        
        moving_layer = self.moving_combo_box.currentText()
        self.moving_combo_box.clear()
        self.moving_combo_box.addItems(layer_names)
        
        fixed_layer = self.fixed_combo_box.currentText()
        self.fixed_combo_box.clear()
        self.fixed_combo_box.addItems(layer_names)
    
        # if the selected layer has been deleted, unselect from the combo boxes
        if self.moving_combo_box.currentText() not in layer_names:
            self.moving_combo_box.setCurrentText(None)
        else:
            self.moving_combo_box.setCurrentText(moving_layer)
            
        if self.fixed_combo_box.currentText() not in layer_names:
            self.fixed_combo_box.setCurrentText(None)
        else:
            self.fixed_combo_box.setCurrentText(fixed_layer)
        
    def _get_image_layer_names(self):
        return [x.name for x in self.viewer.layers if (isinstance(x, Image) or isinstance(x, Labels))]
        
    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
        