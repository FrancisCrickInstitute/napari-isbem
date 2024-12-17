import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout


from napari_sbem_viewer._views.acquisition import TCPSettings, AcquisitionSettings, AcquisitionInfo, ROISettings
from napari_sbem_viewer._models import AcquisitionModel
from napari_sbem_viewer._controllers import AcquisitionController


class AcquisitionWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.acquisition_model = AcquisitionModel(self.viewer)
        self.tcp_settings = TCPSettings()
        self.acquisition_settings = AcquisitionSettings()
        self.roi_settings = ROISettings()
        self.acquisition_info = AcquisitionInfo()
        self.acquisition_controller = AcquisitionController(
            self.acquisition_model,
            self.tcp_settings,
            self.acquisition_settings,
            self.roi_settings,
            self.acquisition_info)
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.tcp_settings)
        self.layout().addWidget(self.acquisition_settings)
        self.layout().addWidget(self.roi_settings)
        self.layout().addWidget(self.acquisition_info)
        self.layout().addStretch(1)
        