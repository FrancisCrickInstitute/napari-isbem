import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QVBoxLayout

from napari_sbem_viewer._views.registration import UploadXrayStack, SelectImages, RegistrationOptions
from napari_sbem_viewer._controllers import ManualRegistrationController
from napari_sbem_viewer._models import ManualRegistrationModel


class RegistrationWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        
        self.viewer = napari_viewer
        
        self.upload_xray_stack = UploadXrayStack(napari_viewer)
        # self.layout().addWidget(self.upload_xray_stack)
        
        self.select_images = SelectImages(self.viewer, parent=self)
        self.registration_options = RegistrationOptions(napari_viewer, parent=self)
        self.manual_registration_model = ManualRegistrationModel(self.viewer)
        
        self.manual_registration_controller = ManualRegistrationController(
            self.registration_options.manual_registration,
            self.select_images,
            self.manual_registration_model)
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.select_images)
        self.layout().addWidget(self.registration_options)
        self.layout().addStretch(1)

    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
    