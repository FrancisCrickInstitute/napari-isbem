import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout

from napari_sbem_viewer._widgets.sbemimage_integration import TCPSettings, AcquisitionSettings
from napari_sbem_viewer.live_viewer import LiveViewer
from napari_sbem_viewer.tcp_server import TCPServer
from napari_sbem_viewer.utils import Trigger
from queue import Queue


class SBEMimageIntegration(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.live_viewer = LiveViewer(self.viewer)
        self.trigger = Trigger()
        self.trigger.signal.connect(self.process_request)
        self.response_queue = Queue()
        self.tcp_server = TCPServer('localhost', 8888, self.trigger, self.response_queue)
            
        self.setLayout(QVBoxLayout())
        self.tcp_settings = TCPSettings(self.viewer, self.tcp_server)
        self.layout().addWidget(self.tcp_settings)
        self.acquisition_settings = AcquisitionSettings(self.viewer, self.live_viewer)
        self.layout().addWidget(self.acquisition_settings)
        self.layout().addStretch(1)
        
    def process_request(self):
        request = self.trigger.queue.get()
        # validate_request(request)
        commands = []
        slice_thickness = request['slice_thickness']
        self.live_viewer.pixel_size_z = slice_thickness
        ov_dirs = request['overviews']['ov_dirs']
        self.acquisition_settings._update_overview_dirs(ov_dirs)
        self.response_queue.put({'commands': commands})
        