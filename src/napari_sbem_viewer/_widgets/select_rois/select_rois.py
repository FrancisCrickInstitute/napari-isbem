import napari
from qtpy.QtWidgets import QGroupBox, QWidget, QVBoxLayout
import numpy as np

from napari_sbem_viewer._widgets.select_rois import ROIList, AdjustROI


class SelectROIs(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        self.bbox_layer_config = {'edge_width': 0.5}
        self.bbox_layer = None
        
        self.roi_list = ROIList(self.viewer, parent=self, bbox_layer_config=self.bbox_layer_config)
        self.roi_list.roi_list_widget.currentRowChanged.connect(self._on_change_roi_list)
        self.layout().addWidget(self.roi_list)
        
        self.adjust_roi = AdjustROI(self.viewer, parent=self)
        self.adjust_roi.setVisible(False)
        self.layout().addWidget(self.adjust_roi)

        self.viewer.layers.events.removed.connect(self._on_remove_bbox_layer)
        self.layout().addStretch(1)
        
    def _on_remove_bbox_layer(self, event):
        if event.value == self.bbox_layer:
            self.bbox_layer = None
            self.roi_list.roi_list_widget.clear()
            
    def _on_change_roi_list(self, current_row):
        self.adjust_roi._render_adjust_roi_widget(current_row)
