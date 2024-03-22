import napari
from napari.qt.threading import thread_worker
from qtpy.QtWidgets import QWidget, QHBoxLayout, QPushButton


class AcquisitionControls(QWidget):
    def __init__(self,
                 viewer: napari.Viewer,
                 acquisition
                 ):
        super().__init__()
        self.viewer = viewer
        self.acquisition = acquisition
        self.setLayout(QHBoxLayout())
        
        # Add start and stop acquisition buttons
        self.start_btn = QPushButton("Start acquisition")
        self.pause_btn = QPushButton("Pause acquisition", enabled=False)
        self.layout().addWidget(self.start_btn)
        self.layout().addWidget(self.pause_btn)

    def reset_ui_start(self):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        
    def reset_ui_pause(self):
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
            