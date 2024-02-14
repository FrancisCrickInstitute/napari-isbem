import napari
from magicgui.widgets import FileEdit
from magicgui.types import FileDialogMode
from qtpy.QtWidgets import QPushButton, QGridLayout, QGroupBox

from napari_sbem_viewer.util import LiveViewer
    

class OverviewDirectory(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 live_viewer: LiveViewer,
                 ):
        super().__init__("Overview directory")
        self.viewer = viewer
        self.live_viewer = live_viewer
        
        self.setLayout(QGridLayout())
        self.filename_edit = FileEdit(
            nullable=True,
            mode=FileDialogMode.EXISTING_DIRECTORY)
        self.layout().addWidget(self.filename_edit.native, 0, 0, 1, 3)
        
        self.watch_btn = QPushButton("Watch")
        self.watch_btn.clicked.connect(self._on_click_watch_folder)
        self.layout().addWidget(self.watch_btn, 1, 0)
        
        self.stop_watching_btn = QPushButton("Pause", enabled=False)
        self.stop_watching_btn.clicked.connect(self._on_click_stop_watching_folder)
        self.layout().addWidget(self.stop_watching_btn, 1, 1)
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_click_reset)
        self.layout().addWidget(self.reset_btn, 1, 2)

    def _on_click_watch_folder(self):
        if str(self.filename_edit.value) == ".":
            return
        self.live_viewer.watch_folder(self.filename_edit.value)
        self.watch_btn.setEnabled(False)
        self.stop_watching_btn.setEnabled(True)
        
    def _on_click_stop_watching_folder(self):
        self.live_viewer.stop_watching()
        self.watch_btn.setEnabled(True)
        self.stop_watching_btn.setEnabled(False)
        
    def _on_click_reset(self):
        self.live_viewer.reset()
        self.live_viewer.stop_watching()
        self.filename_edit.value = None
        self.watch_btn.setEnabled(True)
        self.stop_watching_btn.setEnabled(False)