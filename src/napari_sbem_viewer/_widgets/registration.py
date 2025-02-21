import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QVBoxLayout

from napari_sbem_viewer._views import RegistrationView
from napari_sbem_viewer._controllers import RegistrationController
from napari_sbem_viewer._models import StackViewer, RegistrationModel


class RegistrationWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        stack_viewer = StackViewer(napari.Viewer(show=False), parent=self)
        self.registration_model = RegistrationModel(self.viewer, stack_viewer)
        self.view = RegistrationView()
        self.controller = RegistrationController(self.view, self.registration_model)
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.view)
        self.layout().addStretch(1)
        