import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout, QMessageBox

from napari_sbem_viewer._views.rois import ROIList, AddBoundingBoxes, AddLabels


class SelectROIsWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        self.bbox_layer_config = {'edge_width': 5}
        self.bbox_layer = None
        
        self.add_labels = AddLabels(self.viewer, parent=self)
        self.layout().addWidget(self.add_labels)
        
        self.upload_labels = AddBoundingBoxes(self.viewer, parent=self)
        self.upload_labels.upload_button.clicked.connect(self._on_upload_labels)
        self.layout().addWidget(self.upload_labels)
        
        self.roi_list = ROIList(self.viewer, parent=self, bbox_layer_config=self.bbox_layer_config)
        self.layout().addWidget(self.roi_list)
        
        self.viewer.layers.events.removed.connect(self._on_remove_bbox_layer)
        self.layout().addStretch(1)
        
    def _on_remove_bbox_layer(self, event):
        if event.value == self.bbox_layer:
            self.bbox_layer = None
            self.roi_list.model.removeRows(0, self.roi_list.model.rowCount())
            
    def _on_upload_labels(self):
        layer = self.upload_labels.get_layer()
        if layer.ndim != 3:
            QMessageBox.critical(self, "Error", "Labels layer must be 3D")
            return
        if layer is None:
            return
        self.roi_list.add_bounding_boxes_from_labels(layer)
        