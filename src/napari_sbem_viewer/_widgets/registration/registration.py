import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QVBoxLayout

from napari_sbem_viewer._widgets.registration import UploadXrayStack, ManualRegistration, SelectImages, AlignPlanes, RegistrationOptions


class Registration(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        
        self.upload_xray_stack = UploadXrayStack(napari_viewer)
        # self.layout().addWidget(self.upload_xray_stack)
        
        self.select_images = SelectImages(self.viewer, parent=self)
        self.layout().addWidget(self.select_images)
        
        self.registration_options = RegistrationOptions(napari_viewer, parent=self)
        self.layout().addWidget(self.registration_options)
        
        # self.align_planes = AlignPlanes(napari_viewer, parent=self)
        # self.layout().addWidget(self.align_planes)
        
        # self.manual_registration = ManualRegistration(napari_viewer, parent=self)
        self.select_images.moving_combo_box.currentTextChanged.connect(self.registration_options.manual_registration._on_select_moving_image)
        self.select_images.fixed_combo_box.currentTextChanged.connect(self.registration_options.manual_registration._on_select_fixed_image)
        # self.layout().addWidget(self.manual_registration)
        self.layout().addStretch(1)

    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
    