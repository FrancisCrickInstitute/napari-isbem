import napari
from napari.qt import QtViewer
from qtpy.QtCore import Qt


class StackViewer(QtViewer):
    def __init__(self, viewer: napari.Viewer, parent=None):
        super().__init__(viewer)
        if parent is not None:
            self.setParent(parent)
        self.viewer = viewer
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.viewer.dims.ndisplay = 3

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        