import napari
from qtpy.QtWidgets import QGridLayout, QGroupBox, QComboBox, QLabel
from napari_bbox import BoundingBoxLayer


class SelectROILayer(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 ):
        super().__init__("Select images")
        self.viewer = viewer
        self.setLayout(QGridLayout())
        
        self.layout().addWidget(QLabel("ROI layer"))
        self.combo_box = QComboBox()
        self.layout().addWidget(self.combo_box)
        
        self.viewer.layers.events.removed.connect(self._update_selections)
        self.viewer.layers.events.inserted.connect(self._update_selections)
        self._update_selections()

    def get_bbox_layer(self):
        layer_name = self.combo_box.currentText()
        return self._get_layer(layer_name)
        
    def _update_selections(self):
        layer_names = self._get_bbox_layer_names()
        
        bbox_layer = self.combo_box.currentText()
        self.combo_box.clear()
        self.combo_box.addItems(layer_names)
    
        # if the selected layer has been deleted, unselect from the combo boxes
        if self.combo_box.currentText() not in layer_names:
            self.combo_box.setCurrentText(None)
        else:
            self.combo_box.setCurrentText(bbox_layer)
        
    def _get_bbox_layer_names(self):
        return [x.name for x in self.viewer.layers if isinstance(x, BoundingBoxLayer)]
        
    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
        