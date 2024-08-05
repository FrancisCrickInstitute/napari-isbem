import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel

from napari_sbem_viewer._widgets.select_rois import ROIList


class SelectROIs(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        self.bbox_layer_config = {'edge_width': 5}
        self.bbox_layer = None
        self.viewer.dims.events.current_step.connect(self._on_change_z_depth)
        
        self.current_z_depth_label = QLabel('Current Z: ')
        self.layout().addWidget(self.current_z_depth_label)
        
        self.roi_list = ROIList(self.viewer, parent=self, bbox_layer_config=self.bbox_layer_config)
        self.layout().addWidget(self.roi_list)
        
        self.viewer.layers.events.removed.connect(self._on_remove_bbox_layer)
        self.layout().addStretch(1)
        
    def _on_change_z_depth(self):
        z_depth = self.viewer.dims.point[0]
        self.current_z_depth_label.setText(f"Current Z: {z_depth:.2f}µm")
        
    def _on_remove_bbox_layer(self, event):
        if event.value == self.bbox_layer:
            self.bbox_layer = None
            self.roi_list.model.clear()