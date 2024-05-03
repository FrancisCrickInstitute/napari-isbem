import napari
from napari.layers.base._base_constants import ActionType
from napari.layers.points._points_constants import Mode
from qtpy.QtWidgets import QPushButton, QGridLayout, QLabel, QSpinBox, QWidget, QSlider, QProgressBar
from qtpy.QtCore import Qt
import numpy as np
from napari.qt import QtViewer
from copy import copy


class AlignPlanes(QWidget):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__(parent=parent)
        self.setMinimumWidth(180)
        self.viewer = viewer
        self.setLayout(QGridLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.align_planes_window = False
        
        self.show_button = QPushButton("Show")
        self.show_button.clicked.connect(self._on_click_show)
        self.layout().addWidget(self.show_button, 0, 0, 1, 2)
        
        self.layout().addWidget(QLabel("Rotate Z-Y"), 1, 0)
        self.zy_degrees_spinbox = QSpinBox(minimum=-180, maximum=180)
        self.zy_degrees_spinbox.valueChanged.connect(self._on_change_zy_degrees)
        self.layout().addWidget(self.zy_degrees_spinbox, 1, 1)
        
        self.layout().addWidget(QLabel("Rotate Z-X"), 2, 0)
        self.zx_degrees_spinbox = QSpinBox(minimum=-180, maximum=180)
        self.zx_degrees_spinbox.valueChanged.connect(self._on_change_zx_degrees)
        self.layout().addWidget(self.zx_degrees_spinbox, 2, 1)
        
        self.layout().addWidget(QLabel("Position"), 3, 0)
        self.position_slider = QSlider(Qt.Horizontal)
        self.layout().addWidget(self.position_slider, 3, 1)
        
        self.register_button = QPushButton("Register")
        self.layout().addWidget(self.register_button, 4, 0, 1, 2)
        
        self.progress_bar = QProgressBar(value=0)
        self.layout().addWidget(self.progress_bar, 5, 0, 1, 2)
        self.layout().setRowStretch(self.layout().rowCount(), 1)
        
        
    def _change_normal(self):
        normal = [[1], 
                  [0], 
                  [0]]
        transform_matrix_zy = [
            [np.cos(np.radians(self.zy_degrees_spinbox.value())), -np.sin(np.radians(self.zy_degrees_spinbox.value())), 0],
            [np.sin(np.radians(self.zy_degrees_spinbox.value())), np.cos(np.radians(self.zy_degrees_spinbox.value())), 0],
            [0, 0, 1]
        ]
        transform_matrix_zx = [
            [np.cos(np.radians(self.zx_degrees_spinbox.value())), 0, np.sin(np.radians(self.zx_degrees_spinbox.value()))],
            [0, 1, 0],
            [-np.sin(np.radians(self.zx_degrees_spinbox.value())), 0, np.cos(np.radians(self.zx_degrees_spinbox.value()))],
        ]
        normal = np.matmul(transform_matrix_zy, normal)
        normal = np.matmul(transform_matrix_zx, normal)
        self.align_planes_window.viewer.layers['plane'].plane.normal = normal
        
    def _on_change_zy_degrees(self):
        self._change_normal()
        
    def _on_change_zx_degrees(self):
        self._change_normal()
        
    def _on_click_show(self):
        self._init_align_planes_window()

        moving_layer = self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()
        if self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer() is None:
            return
        
        moving_layer = copy(moving_layer)
        moving_layer.name = 'image'
        moving_layer_plane = copy(moving_layer)
        moving_layer_plane.name = 'plane'
        moving_layer_plane.depiction = 'plane'
        moving_layer_plane.colormap = 'cyan'
        
        self.align_planes_window.viewer.add_layer(moving_layer)
        self.align_planes_window.viewer.add_layer(moving_layer_plane)
        self.align_planes_window.show()
        
    def _init_align_planes_window(self):
        self.align_planes_window = QtViewer(napari.Viewer(show=False))
        self.align_planes_window.setParent(self)
        self.align_planes_window.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.align_planes_window.viewer.dims.ndisplay = 3
        