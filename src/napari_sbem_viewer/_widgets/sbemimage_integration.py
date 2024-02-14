import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout

from napari_sbem_viewer.util import TCPClient
from napari_sbem_viewer._widgets.tcp_settings import TCPSettings
from napari_sbem_viewer._widgets import OverviewDirectory, AcquisitionControls, AcquisitionSettings
from napari_sbem_viewer.util import LiveViewer


class SBEMimageIntegration(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.live_viewer = LiveViewer(self.viewer)
        self.setLayout(QVBoxLayout())
        
        self.tcp_client = TCPClient('localhost', 8888)
        
        self.tcp_settings = TCPSettings(self.viewer, self.tcp_client)
        self.layout().addWidget(self.tcp_settings)
        
        self.overview_directory = OverviewDirectory(self.viewer, self.live_viewer)
        self.layout().addWidget(self.overview_directory)
        
        # Add acquisition settings form
        self.acquisition_settings = AcquisitionSettings(self.viewer, self.live_viewer)
        self.layout().addWidget(self.acquisition_settings)
        
        self.acquisition_controls = AcquisitionControls(self.viewer, self.tcp_client)
        self.layout().addWidget(self.acquisition_controls)
