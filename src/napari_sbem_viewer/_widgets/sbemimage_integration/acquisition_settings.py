import napari
from qtpy.QtWidgets import QGridLayout, QLabel, QSpinBox, QGroupBox, QVBoxLayout, QComboBox
from napari_bbox import BoundingBoxLayer

from napari_sbem_viewer.live_viewer import LiveViewer

DEFAULT_COARSE_THICKNESS = 100
DEFAULT_FINE_THICKNESS = 50


class AcquisitionSettings(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 live_viewer: LiveViewer,
                 ):
        super().__init__("Acquisition settings")
        self.viewer = viewer
        self.live_viewer = live_viewer
        self.setLayout(QVBoxLayout())
        self.overview_dirs = []
        
        # ------- Overview directory settings-------
        self.layout().addWidget(QLabel("Overview directory"))
        self.overview_combo_box = QComboBox()
        self.overview_combo_box.addItem("")
        self.overview_combo_box.currentTextChanged.connect(self._on_select_overview_dir)
        self.layout().addWidget(self.overview_combo_box)
        
        # --------- ROI layer settings---------
        self.layout().addWidget(QLabel("ROI layer"))
        self.roi_combo_box = QComboBox()
        self.layout().addWidget(self.roi_combo_box)
        self.viewer.layers.events.removed.connect(self._update_roi_selections)
        self.viewer.layers.events.inserted.connect(self._update_roi_selections)
        self._update_roi_selections()
        
        # ------- Cutting depth settings-------
        cutting_depth_layout = QGridLayout()
        cutting_depth_layout.addWidget(QLabel("Cutting thickness coarse (nm)"), 0, 0)
        self.coarse_thickness_spinbox = QSpinBox(maximum=999, value=DEFAULT_COARSE_THICKNESS)
        cutting_depth_layout.addWidget(self.coarse_thickness_spinbox, 0, 1)
        cutting_depth_layout.addWidget(QLabel("Cutting thickness fine (nm)"), 1, 0)
        self.fine_thickness_spinbox = QSpinBox(maximum=999, value=DEFAULT_FINE_THICKNESS)
        cutting_depth_layout.addWidget(self.fine_thickness_spinbox, 1, 1)
        self.layout().addLayout(cutting_depth_layout)
        
    def get_bbox_layer(self):
        layer_name = self.roi_combo_box.currentText()
        return self._get_layer(layer_name)
        
    def _update_roi_selections(self):
        layer_names = self._get_bbox_layer_names()
        bbox_layer = self.roi_combo_box.currentText()
        self.roi_combo_box.clear()
        self.roi_combo_box.addItem("")
        self.roi_combo_box.addItems(layer_names)
    
        # if the selected layer has been deleted, unselect from the combo boxes
        if self.roi_combo_box.currentText() not in layer_names:
            self.roi_combo_box.setCurrentIndex(0)
        else:
            self.roi_combo_box.setCurrentText(bbox_layer)
        
    def _get_bbox_layer_names(self):
        return [x.name for x in self.viewer.layers if isinstance(x, BoundingBoxLayer)]
        
    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None    
        
    def _update_overview_dirs(self, overview_dirs):
        if set(overview_dirs) != set(self.overview_dirs):
            self.overview_combo_box.clear()
            # add an empty item to the combo box
            self.overview_combo_box.addItem("")
            self.overview_combo_box.addItems(overview_dirs)
            self.overview_dirs = overview_dirs

    def _on_select_overview_dir(self):
        if self.overview_combo_box.currentIndex() == 0:
            self._on_reset_overview()
            return
        self.live_viewer.init_images(self.overview_combo_box.currentText())
        
    def _on_reset_overview(self):
        self.live_viewer.reset()
        