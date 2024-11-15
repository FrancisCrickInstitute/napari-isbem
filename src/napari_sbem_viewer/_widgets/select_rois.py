import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout, QMessageBox

from napari_sbem_viewer._views.rois import ROIList, AddBoundingBoxes, AddLabels
from napari_sbem_viewer._models import SelectROIsModel
from napari_sbem_viewer._controllers import SelectROIsController


class SelectROIsWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        
        self.add_labels = AddLabels(parent=self)
        self.add_bounding_boxes = AddBoundingBoxes(parent=self)
        self.roi_list = ROIList(parent=self)
        
        self.select_rois_model = SelectROIsModel(self.viewer)
        self.select_rois_controller = SelectROIsController(
            self.select_rois_model,
            self.add_labels,
            self.add_bounding_boxes,
            self.roi_list
        )

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.add_labels)
        self.layout().addWidget(self.add_bounding_boxes)
        self.layout().addWidget(self.roi_list)
        self.layout().addStretch(1)
        