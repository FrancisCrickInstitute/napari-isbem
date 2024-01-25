import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout

from napari_sbem_viewer.util import TCPClient
from napari_sbem_viewer._widgets.tcp_settings import TCPSettings
from napari_sbem_viewer._widgets import OverviewDirectory, AcquisitionControls, AcquisitionSettings


class SBEMimageIntegration(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        
        self.tcp_client = TCPClient('localhost', 8888)
        
        tcp_settings = TCPSettings(self.viewer, self.tcp_client)
        self.layout().addWidget(tcp_settings)
        
        overview_directory = OverviewDirectory(self.viewer)
        self.layout().addWidget(overview_directory)
        
        # Add acquisition settings form
        acquisition_settings = AcquisitionSettings(self.viewer)
        self.layout().addWidget(acquisition_settings)
        
        acquisition_controls = AcquisitionControls(self.viewer, self.tcp_client)
        self.layout().addWidget(acquisition_controls)
