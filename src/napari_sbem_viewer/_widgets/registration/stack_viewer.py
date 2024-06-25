from copy import copy

import napari
from napari.qt import QtViewer
from napari.layers.points._points_constants import Mode
from qtpy.QtCore import Qt


class StackViewer(QtViewer):
    def __init__(self, viewer: napari.Viewer, parent=None):
        super().__init__(viewer)
        if parent is not None:
            self.setParent(parent)
        self.viewer = viewer
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        # self.setWindowFlags(Qt.Tool)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        