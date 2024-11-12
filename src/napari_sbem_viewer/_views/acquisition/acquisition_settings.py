import napari
from qtpy.QtWidgets import QGridLayout, QLabel, QSpinBox, QGroupBox, QVBoxLayout, QComboBox
from napari_bbox import BoundingBoxLayer

from napari.layers import Labels


DEFAULT_FINE_THICKNESS = 50


class AcquisitionSettings(QGroupBox):
    def __init__(self, viewer: napari.Viewer):
        super().__init__("Acquisition settings")
        self.setLayout(QVBoxLayout())
        self.viewer = viewer
        
        # ------- Overview directory settings-------
        self.layout().addWidget(QLabel("Overview directory"))
        self.overview_combo_box = QComboBox()
        self.overview_combo_box.addItem("")
        self.layout().addWidget(self.overview_combo_box)
        
        # --------- ROI layer settings---------
        self.layout().addWidget(QLabel("ROI layer"))
        self.roi_combo_box = QComboBox()
        self.roi_combo_box.setEnabled(False)
        self.layout().addWidget(self.roi_combo_box)
        self.roi_layer = None
        
        # ------- Cutting depth settings-------
        cutting_depth_layout = QGridLayout()
        self.coarse_thickness_label = QLabel("")
        cutting_depth_layout.addWidget(QLabel("Coarse thickness (nm):"), 0, 0)
        cutting_depth_layout.addWidget(self.coarse_thickness_label, 0, 1)
        self.fine_thickness_spinbox = QSpinBox(maximum=999, value=DEFAULT_FINE_THICKNESS)
        cutting_depth_layout.addWidget(QLabel("Fine thickness (nm):"), 1, 0)
        cutting_depth_layout.addWidget(self.fine_thickness_spinbox, 1, 1)
        self.layout().addLayout(cutting_depth_layout)
        
    def update_overview_dirs(self, ov_dirs):
        curr_dirs = self.get_current_overview_dirs()
        if set(ov_dirs) != set(curr_dirs):
            self.overview_combo_box.clear()
            # add an empty item to the combo box
            self.overview_combo_box.addItem("")
            self.overview_combo_box.addItems(ov_dirs)
        
    def get_roi_layer(self):
        layer_name = self.roi_combo_box.currentText()
        return self._get_layer(layer_name)
    
    def get_current_overview_dirs(self):
        return [self.overview_combo_box.itemText(i) 
                for i in range(1, self.overview_combo_box.count())]
        
    def _get_roi_layer_names(self):
        return [x.name for x in self.viewer.layers if (isinstance(x, BoundingBoxLayer) or isinstance(x, Labels))]
        
    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
        