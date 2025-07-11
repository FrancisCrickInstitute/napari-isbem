import napari
from napari.qt import QtViewer
from qtpy.QtCore import Qt


class StackViewer(QtViewer):
    """Viewer for displaying 3D stacks in napari with a custom window style.
    This viewer is designed to be used as a tool window that stays on top of the main napari viewer.
    It initializes the viewer with a 3D display mode and custom window flags.
    The viewer can be closed without removing it from the napari application, allowing it to be hidden instead.
    """

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
