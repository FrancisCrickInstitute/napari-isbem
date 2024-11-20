import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout

from napari_sbem_viewer._views.rois import DrawROIsView
from napari_sbem_viewer._models import DrawROIsModel
from napari_sbem_viewer._controllers import DrawROIsController


class DrawROIsWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        
        self.draw_rois_view = DrawROIsView(parent=self)
        self.draw_rois_model = DrawROIsModel(self.viewer)
        self.draw_rois_controller = DrawROIsController(
            self.draw_rois_model, 
            self.draw_rois_view
        )

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.draw_rois_view)
        self.layout().addStretch(1)
        