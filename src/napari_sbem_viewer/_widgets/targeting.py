import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout

from napari_sbem_viewer._views import TargetingView
from napari_sbem_viewer._models import DrawROIsModel
from napari_sbem_viewer._controllers import TargetingController


class TargetingWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.draw_rois_model = DrawROIsModel(self.viewer)
        self.view = TargetingView()
        self.controller = TargetingController(self.view, self.draw_rois_model)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.view)
        self.layout().addStretch(1)
        