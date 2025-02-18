import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QVBoxLayout

from napari_sbem_viewer._views.registration import ImageSettings, AlignPlanes, Affine2d, ZAlignment
from napari_sbem_viewer._controllers import RegistrationController
from napari_sbem_viewer._models import StackViewer, RegistrationModel


class RegistrationWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        stack_viewer = StackViewer(napari.Viewer(show=False), parent=self)
        self.registration_model = RegistrationModel(self.viewer, stack_viewer)
        self.align_planes = AlignPlanes(parent=self)
        self.z_alignment = ZAlignment(parent=self)
        self.affine_2d = Affine2d(parent=self)
        self.image_settings = ImageSettings(self.viewer, parent=self)
        
        self.registration_controller = RegistrationController(
            self.registration_model,
            self.align_planes,
            self.z_alignment,
            self.affine_2d,
            self.image_settings)
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.image_settings)
        self.layout().addWidget(self.align_planes)
        self.layout().addWidget(self.z_alignment)
        self.layout().addWidget(self.affine_2d)
        self.layout().addStretch(1)
        