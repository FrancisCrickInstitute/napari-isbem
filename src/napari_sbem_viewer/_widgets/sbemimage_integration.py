import napari
from napari.qt import thread_worker
from qtpy.QtWidgets import QWidget, QVBoxLayout, QMessageBox

from napari_sbem_viewer.util import TCPClient
from napari_sbem_viewer._widgets.tcp_settings import TCPSettings
from napari_sbem_viewer._widgets import OverviewDirectory, AcquisitionControls, AcquisitionSettings, SelectROILayer
from napari_sbem_viewer.util import LiveViewer
from napari_sbem_viewer.acquisition import Acquisition, StartAcquisitionError


class SBEMimageIntegration(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.live_viewer = LiveViewer(self.viewer)
        self.setLayout(QVBoxLayout())        
        
        self.tcp_client = TCPClient('localhost', 8888)
        self.acquisition = Acquisition(self.live_viewer, self.tcp_client)
        
        self.tcp_settings = TCPSettings(self.viewer, self.tcp_client)
        self.layout().addWidget(self.tcp_settings)
        
        self.overview_directory = OverviewDirectory(self.viewer, self.live_viewer, self.tcp_client)
        self.layout().addWidget(self.overview_directory)
        
        self.select_roi_layer = SelectROILayer(self.viewer)
        self.select_roi_layer.combo_box.currentTextChanged.connect(self._on_select_roi_layer)
        self.layout().addWidget(self.select_roi_layer)
        
        # Add acquisition settings form
        self.acquisition_settings = AcquisitionSettings(self.viewer, self.live_viewer)
        self.layout().addWidget(self.acquisition_settings)
        
        self.acquisition_controls = AcquisitionControls(self.viewer, self.acquisition)
        self.acquisition_controls.start_btn.clicked.connect(self._on_click_start)
        self.acquisition_controls.pause_btn.clicked.connect(self._on_click_pause)
        self.layout().addWidget(self.acquisition_controls)
        
        self.layout().addStretch(1)
        
    def _on_select_roi_layer(self):
        self.acquisition.roi_layer = self.select_roi_layer.get_bbox_layer()
        
    def _on_click_start(self):
        @thread_worker(connect={"errored": self._handle_start_acquisition_error, 
                                "finished": self._on_click_pause,
                                "yielded": self.live_viewer.append})
        def start_acquisition():
            yield from self.acquisition.start_acquisition()
        self.acquisition_controls.reset_ui_pause()
        start_acquisition()
        
    def _handle_start_acquisition_error(self, e):
        print(e)
        if isinstance(e, ConnectionRefusedError):
            QMessageBox.warning(self, "Error starting acquisition", """Could not connect to SBEMimage. Check if the TCP server in SBEMimage is running and the host and port are correct.""")
            self.acquisition_controls.reset_ui_start()
        elif isinstance(e, StartAcquisitionError):
            # if there is an error starting the acquisition in sbemimage, reset the ui
            # this could be due to a TCP connection error
            QMessageBox.warning(self, "Error starting acquisition", "Acquisition could not be started.")
            self.acquisition_controls.reset_ui_start()
        elif isinstance(e, FileNotFoundError):
            QMessageBox.warning(self, "Error starting acquisition", "Overview directory is not set.")
            self.acquisition_controls.reset_ui_start()
        else:
            # if there is an error after the acquistion has started, the acquisition
            # must first be paused
            QMessageBox.warning(self, "Error during acquisition", "Error during acquisition process. Pausing acquisition in SBEMimage...")
            self._on_click_pause()
            
    def _on_click_pause(self):
        @thread_worker(connect={"errored": self.acquisition_controls.reset_ui_pause, 
                                "finished": self.acquisition_controls.reset_ui_start})
        def pause_acquisition():
            self.acquisition.pause_acquisition()
        self.acquisition_controls.start_btn.setEnabled(False)
        self.acquisition_controls.pause_btn.setEnabled(False)
        pause_acquisition()
        