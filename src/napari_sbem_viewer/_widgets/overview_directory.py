import napari
from magicgui.widgets import FileEdit
from magicgui.types import FileDialogMode
from qtpy.QtWidgets import QPushButton, QVBoxLayout, QGroupBox, QComboBox, QGridLayout, QMessageBox

from napari_sbem_viewer.util import LiveViewer
    

class OverviewDirectory(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 live_viewer: LiveViewer,
                 tcp_client
                 ):
        super().__init__("Overview directory")
        self.viewer = viewer
        self.live_viewer = live_viewer
        self.tcp_client = tcp_client
        
        self.setLayout(QGridLayout())
        self.combo_box = QComboBox()
        self.combo_box.currentTextChanged.connect(self._on_select_overview_dir)
        self.layout().addWidget(self.combo_box, 0, 0, 1, 2)
        
        self.refresh_btn = QPushButton("Find OV dirs")
        self.refresh_btn.clicked.connect(self._find_overview_dirs)
        self.layout().addWidget(self.refresh_btn, 1, 0)
        
        self.reset_btn = QPushButton("Reset", enabled=False)
        self.reset_btn.clicked.connect(self._on_click_reset)
        self.layout().addWidget(self.reset_btn, 1, 1)
        
    def _find_overview_dirs(self):
        self.combo_box.clear()
        try:
            overview_dirs = self.tcp_client.find_overview_dirs()
            if overview_dirs:
                self.combo_box.addItems(overview_dirs)
        except ConnectionRefusedError:
            QMessageBox.warning(self, "Error starting acquisition", """Could not connect to SBEMimage. Check if the TCP server in SBEMimage is running and the host and port are correct.""")

    def _on_select_overview_dir(self):
        self.live_viewer.init_images(self.combo_box.currentText())
        self.reset_btn.setEnabled(True)
        
    def _on_click_reset(self):
        self.live_viewer.reset()
        self.combo_box.setCurrentIndex(-1)
        self.reset_btn.setEnabled(False)