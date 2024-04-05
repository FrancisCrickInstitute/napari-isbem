import napari
from napari.layers.image.image import Image
from qtpy.QtWidgets import QGridLayout, QGroupBox, QComboBox, QLabel


class SelectROIImage(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 ):
        super().__init__("Select images")
        self.viewer = viewer
        self.setLayout(QGridLayout())
        
        self.layout().addWidget(QLabel("Targetting image"))
        self.combo_box = QComboBox()
        self.layout().addWidget(self.combo_box)
        
        self.viewer.layers.events.removed.connect(self._update_selections)
        self.viewer.layers.events.inserted.connect(self._update_selections)
        
        self._update_selections()
    
    def get_image_layer(self):
        return self._get_layer(self.combo_box.currentText())
        
    def _update_selections(self):
        layer_names = self._get_image_layer_names()
        
        layer = self.combo_box.currentText()
        self.combo_box.clear()
        self.combo_box.addItems(layer_names)
    
        # if the selected layer has been deleted, unselect from the combo boxes 
        if self.combo_box.currentText() not in layer_names:
            self.combo_box.setCurrentText(None)
        else:
            self.combo_box.setCurrentText(layer)
        
    def _get_image_layer_names(self):
        return [x.name for x in self.viewer.layers if isinstance(x, Image)]
        
    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
        