import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QVBoxLayout

from napari_sbem_viewer._views.registration import SelectImages, AlignPlanes, ManualRegistration
from napari_sbem_viewer._controllers import AlignPlanesController, ManualRegistrationController
from napari_sbem_viewer._models import AlignPlanesModel, ManualRegistrationModel, StackViewer


class RegistrationWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        
        self.viewer = napari_viewer
        
        self.select_images = SelectImages(self.viewer, parent=self)
        
        self.align_planes = AlignPlanes(parent=self)
        align_planes_viewer = StackViewer(napari.Viewer(show=False), parent=self)
        self.align_planes_model = AlignPlanesModel(self.viewer, align_planes_viewer)
        self.align_planes_controller = AlignPlanesController(
            self.align_planes_model,
            self.align_planes,
            self.select_images)
        
        self.manual_registration = ManualRegistration(parent=self)
        self.manual_registration_model = ManualRegistrationModel(self.viewer)
        self.manual_registration_controller = ManualRegistrationController(
            self.manual_registration_model,
            self.manual_registration,
            self.select_images)
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.select_images)
        self.layout().addWidget(self.align_planes)
        self.layout().addWidget(self.manual_registration)
        self.layout().addStretch(1)

    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
    