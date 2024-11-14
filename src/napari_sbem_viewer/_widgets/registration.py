import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QVBoxLayout

from napari_sbem_viewer._views.registration import UploadXrayStack, SelectImages, RegistrationOptions
from napari_sbem_viewer._controllers import AlignPlanesController, ManualRegistrationController
from napari_sbem_viewer._models import AlignPlanesModel, ManualRegistrationModel, StackViewer


class RegistrationWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        
        self.viewer = napari_viewer
        
        self.upload_xray_stack = UploadXrayStack(napari_viewer)
        # self.layout().addWidget(self.upload_xray_stack)
        
        self.select_images = SelectImages(self.viewer, parent=self)
        self.registration_options = RegistrationOptions(napari_viewer, parent=self)
        align_planes_viewer = StackViewer(napari.Viewer(show=False), parent=self)
        self.align_planes_model = AlignPlanesModel(self.viewer, align_planes_viewer)
        self.align_planes_controller = AlignPlanesController(
            self.align_planes_model,
            self.registration_options.align_planes,
            self.select_images)
        
        self.manual_registration_model = ManualRegistrationModel(self.viewer)
        self.manual_registration_controller = ManualRegistrationController(
            self.manual_registration_model,
            self.registration_options.manual_registration,
            self.select_images)
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.select_images)
        self.layout().addWidget(self.registration_options)
        self.layout().addStretch(1)

    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
    