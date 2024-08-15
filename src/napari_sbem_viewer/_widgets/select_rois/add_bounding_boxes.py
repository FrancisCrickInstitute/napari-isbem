import napari
from napari.layers.labels.labels import Labels
from qtpy.QtWidgets import QGridLayout, QGroupBox, QComboBox, QLabel, QPushButton


class AddBoundingBoxes(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__("Upload Labels", parent=parent)
        self.viewer = viewer
        self.setLayout(QGridLayout())
        
        self.layout().addWidget(QLabel("Labels layer"))
        self.combo_box = QComboBox()
        self.layout().addWidget(self.combo_box)
        
        self.upload_button = QPushButton("Upload")
        self.layout().addWidget(self.upload_button)
        
        self.viewer.layers.events.inserted.connect(self._update_selections)
        self.viewer.layers.events.removed.connect(self._update_selections)
        self._update_selections()
        
    def _update_selections(self):
        layer_names = self._get_labels_layer_names()
        layer_name = self.combo_box.currentText()
        self.combo_box.clear()
        self.combo_box.addItems(layer_names)
        if self.combo_box.currentText() not in layer_names:
            self.combo_box.setCurrentText(None)
        else:
            self.combo_box.setCurrentText(layer_name)
            
    def get_layer(self):
        try:
            return self.viewer.layers[self.combo_box.currentText()]
        except KeyError:
            return None
        
    def _get_labels_layer_names(self):
        return [x.name for x in self.viewer.layers if isinstance(x, Labels)]
    