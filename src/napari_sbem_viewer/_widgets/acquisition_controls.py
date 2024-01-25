import napari
from qtpy.QtWidgets import QWidget, QHBoxLayout, QPushButton

from napari_sbem_viewer.util import TCPClient


class AcquisitionControls(QWidget):
    def __init__(self,
                 viewer: napari.Viewer,
                 tcp_client: TCPClient
                 ):
        super().__init__()
        self.viewer = viewer
        self.tcp_client = tcp_client
        self.setLayout(QHBoxLayout())
        
        # Add start and stop acquisition buttons
        self.start_btn = QPushButton("Start acquisition")
        self.start_btn.clicked.connect(self._on_click_start)
        self.stop_btn = QPushButton("Stop acquisition", enabled=False)
        self.stop_btn.clicked.connect(self._on_click_stop)
        self.layout().addWidget(self.start_btn)
        self.layout().addWidget(self.stop_btn)
        
    def _on_click_start(self):
        print("Starting acquisition...")
        # TODO: update cutting depths then start acquisition remotely
        if self.tcp_client.send('START'):
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
    
    def _on_click_stop(self):
        print("Stopping acquisition...")
        if self.tcp_client.send('PAUSE', 2):
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            