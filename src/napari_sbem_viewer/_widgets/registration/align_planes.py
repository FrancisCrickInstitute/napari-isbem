import os

import napari
from napari.layers import Layer
from qtpy.QtWidgets import QPushButton, QGridLayout, QLabel, QSpinBox, QWidget, QSlider, QProgressBar, QLabel, QMessageBox
from qtpy.QtCore import Qt
import numpy as np
from napari.qt import QtViewer
from copy import copy

from napari_sbem_viewer._utils.registration_utils import quaternion_from_vectors, line_parametric_equation, find_intersections, calculate_t, rotate_image_3d_sitk


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
        self.align_planes_window = self._init_align_planes_window()
        self.intersection_points = None
        
        self.show_button = QPushButton("Show")
        self.show_button.clicked.connect(self._on_click_show)
        self.layout().addWidget(self.show_button, 0, 0, 1, 2)
        
        self.layout().addWidget(QLabel("Rotate Z-Y"), 1, 0)
        self.zy_degrees_slider = QSlider(Qt.Horizontal)
        self.zy_degrees_slider.setRange(-90, 90)
        self.zy_degrees_slider.valueChanged.connect(self._on_change_angle)
        self.layout().addWidget(self.zy_degrees_slider, 1, 1)
        # self.zy_degrees_spinbox = QSpinBox(minimum=-180, maximum=180)
        # self.zy_degrees_spinbox.valueChanged.connect(self._on_change_angle)
        # self.layout().addWidget(self.zy_degrees_spinbox, 1, 1)
        
        self.layout().addWidget(QLabel("Rotate Z-X"), 2, 0)
        self.zx_degrees_slider = QSlider(Qt.Horizontal)
        self.zx_degrees_slider.setRange(-90, 90)
        self.zx_degrees_slider.valueChanged.connect(self._on_change_angle)
        self.layout().addWidget(self.zx_degrees_slider, 2, 1)
        # self.zx_degrees_spinbox = QSpinBox(minimum=-180, maximum=180)
        # self.zx_degrees_spinbox.valueChanged.connect(self._on_change_angle)
        # self.layout().addWidget(self.zx_degrees_spinbox, 2, 1)
        
        self.layout().addWidget(QLabel("Position"), 3, 0)
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.setSingleStep(1)
        self.position_slider.valueChanged.connect(self._on_update_position)
        self.layout().addWidget(self.position_slider, 3, 1)
        
        # self.layout().addWidget(QLabel("Select save location"), 4, 0, 1, 2)
        # self.select_dir = SelectDir(self)
        # self.select_dir.dir_line.textChanged.connect(self._on_select_dir)
        # self.layout().addWidget(self.select_dir, 5, 0, 1, 2)
        
        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self._on_click_register)
        self.layout().addWidget(self.register_button, 5, 0, 1, 2)
        
        # self.progress_bar = QProgressBar(value=0)
        # self.layout().addWidget(self.progress_bar, 5, 0, 1, 2)

        self.parentWidget().parentWidget().select_images.moving_combo_box.currentTextChanged.connect(self._on_select_moving_image)
        self.parentWidget().parentWidget().select_images.fixed_combo_box.currentTextChanged.connect(self._on_select_fixed_image)
        self.layout().setRowStretch(self.layout().rowCount(), 1)
        
    def _on_select_dir(self):
        if self._get_save_path() is None:
            self.select_dir.dir_line.setText('')
            
    def _get_save_path(self):
        save_path = self.select_dir.dir_line.text()
        if not os.path.exists(save_path):
            QMessageBox.warning(self, "Invalid save location", "Selected folder does not exist.")
            return None
        if len(os.listdir(save_path)):
            QMessageBox.warning(self, "Invalid save location", "Selected folder is not empty.")
            return None
        if not save_path.endswith('.ome.zarr'):
            QMessageBox.warning(self, "Invalid save location", "Selected folder must end with '.ome.zarr'.")
            return None
        return save_path
        
    def _on_change_angle(self):
        normal = self._calculate_normal()
        self.align_planes_window.viewer.layers['plane'].plane.normal = normal
        self.update_position_slider()
        
    def _calculate_normal(self):
        normal = np.asarray([[1], [0], [0]])
        transform_matrix_zy = np.asarray([
            [np.cos(np.radians(self.zy_degrees_slider.value())), -np.sin(np.radians(self.zy_degrees_slider.value())), 0],
            [np.sin(np.radians(self.zy_degrees_slider.value())), np.cos(np.radians(self.zy_degrees_slider.value())), 0],
            [0, 0, 1]
        ])
        transform_matrix_zx = np.asarray([
            [np.cos(np.radians(self.zx_degrees_slider.value())), 0, np.sin(np.radians(self.zx_degrees_slider.value()))],
            [0, 1, 0],
            [-np.sin(np.radians(self.zx_degrees_slider.value())), 0, np.cos(np.radians(self.zx_degrees_slider.value()))],
        ])
        normal = np.matmul(transform_matrix_zy, normal)
        normal = np.matmul(transform_matrix_zx, normal)
        
        return normal.T[0]

    def update_position_slider(self):
        layer = self.align_planes_window.viewer.layers['plane']
        points = find_intersections([0, 0, 0], layer.data.shapes[-1], np.array(layer.plane.position), np.array(layer.plane.normal))
        if len(points) != 2:
            return
        self.intersection_points = [points[0], points[1]]
        t = calculate_t(points[0], points[1], np.array(layer.plane.position))
        self.position_slider.setValue(int(t * 1000))
        
    def _on_update_position(self):
        if self.intersection_points is None or len(self.intersection_points) != 2:
            return
        t = self.position_slider.value() / 1000
        layer = self.align_planes_window.viewer.layers['plane']
        layer.plane.position = line_parametric_equation(self.intersection_points[0], self.intersection_points[1], t)
        
    def _on_click_show(self):
        moving_layer = self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()
        if self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer() is None:
            return
        
        self.align_planes_window.viewer.layers.clear()
        
        moving_layer = copy(moving_layer)
        moving_layer.affine = None
        moving_layer.name = 'image'
        moving_layer.blending = 'translucent'
        moving_layer_plane = copy(moving_layer)
        moving_layer_plane.blending = 'translucent_no_depth'
        moving_layer_plane.name = 'plane'
        moving_layer_plane.depiction = 'plane'
        moving_layer_plane.colormap = 'cyan'
        
        shape = moving_layer.data.shapes[-1]
        moving_layer_plane.plane.position = moving_layer_plane.data_to_world((shape[0] / 2, shape[1] / 2, shape[2] / 2))
        
        self.align_planes_window.viewer.add_layer(moving_layer)
        self.align_planes_window.viewer.add_layer(moving_layer_plane)
        self.zy_degrees_slider.setValue(0)
        self.zx_degrees_slider.setValue(0)
        self._on_change_angle()
        self.position_slider.setValue(500)
        self._on_update_position()
        

        self.update_position_slider()
        self.align_planes_window.show()
        
    def _update_3d_viewer(self):
        pass
        
    def _on_select_moving_image(self):
        pass
    
    def _on_select_fixed_image(self):
        pass
        
    def _init_align_planes_window(self):
        window = QtViewer(napari.Viewer(show=False))
        window.setParent(self)
        window.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        window.viewer.dims.ndisplay = 3
        return window
        
    def _on_click_register(self):
        normal = self._calculate_normal()
        image_layer = self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()
        rotated_layer = rotate_layer(image_layer, np.asarray([0, 0, 1]), np.asarray(normal[::-1]))
        self.viewer.add_layer(rotated_layer)
        
        
def rotate_layer(layer, v1, v2):
    quaternion = quaternion_from_vectors(v1, v2)
    rotated_data = []
    for pyramid_level in layer.data:
        rotated_data.append(rotate_image_3d_sitk(pyramid_level.compute(), quaternion))
    rotated_layer = Layer.create(rotated_data, {'scale': layer.scale, 'name': layer.name + ' (rotated)'}, 'image')
    return rotated_layer
