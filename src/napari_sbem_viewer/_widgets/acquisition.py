import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout


from napari_sbem_viewer._views import AcquisitionView
from napari_sbem_viewer._models import AcquisitionModel
from napari_sbem_viewer._controllers import AcquisitionController


class AcquisitionWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.acquisition_model = AcquisitionModel(self.viewer)
        self.view = AcquisitionView()
        self.controller = AcquisitionController(self.view, self.acquisition_model)
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.view)
        self.layout().addStretch(1)
        