import os
from copy import copy

import napari
from napari.layers import Image
from napari._qt.widgets._slider_compat import QDoubleSlider
from napari.layers import Layer
from qtpy.QtWidgets import QPushButton, QFormLayout, QFileDialog, QGridLayout, QLabel, QWidget, QLabel, QMessageBox
from qtpy.QtCore import Qt
import numpy as np

from napari_sbem_viewer._widgets.registration import StackViewer
from napari_sbem_viewer._utils.registration_utils import (quaternion_from_vectors, 
                                                          line_parametric_equation, 
                                                          find_intersections, 
                                                          calculate_t, 
                                                          rotate_image_3d_sitk, 
                                                          rotation_matrix_from_zy_zx_angles,
                                                          is_rotation_matrix,
                                                          decompose_rotation_matrix,
                                                          rotation_matrix_from_zy_zx_angles)
from napari_sbem_viewer._utils.image_utils import save_ome_zarr, create_image_pyramid, get_pyramid_scales


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
        self.rotated_layer = None
        
        self.align_planes_button = QPushButton("Upload transform")
        self.align_planes_button.clicked.connect(self._on_click_upload_transform)
        self.layout().addWidget(self.align_planes_button, 0, 0, 1, 2)
        
        self.save_transform_button = QPushButton("Save transform")
        self.save_transform_button.clicked.connect(self._on_click_save_transform)
        self.layout().addWidget(self.save_transform_button, 1, 0)
        
        self.save_ome_zarr_button = QPushButton("Save as OME-Zarr")
        self.save_ome_zarr_button.clicked.connect(self._on_click_save_ome_zarr)
        self.layout().addWidget(self.save_ome_zarr_button, 1, 1)
        
        self.show_button = QPushButton("Show")
        self.show_button.clicked.connect(self._on_click_show)
        self.layout().addWidget(self.show_button, 2, 0, 1, 2)
        
        form_layout = QFormLayout()
        self.zy_degrees_slider = QDoubleSlider(Qt.Horizontal)
        self.zy_degrees_slider.setRange(-90, 90)
        self.zy_degrees_slider.setDecimals(1)
        self.zy_degrees_slider.valueChanged.connect(self._on_change_angle)
        form_layout.addRow(QLabel("Rotate Z-Y"), self.zy_degrees_slider)
        self.zx_degrees_slider = QDoubleSlider(Qt.Horizontal)
        self.zx_degrees_slider.setRange(-90, 90)
        self.zx_degrees_slider.setDecimals(1)
        self.zx_degrees_slider.valueChanged.connect(self._on_change_angle)
        form_layout.addRow(QLabel("Rotate Z-X"), self.zx_degrees_slider)
        self.position_slider = QDoubleSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 1)
        self.position_slider.setSingleStep(0.01)
        self.position_slider.valueChanged.connect(self._on_update_position)
        form_layout.addRow(QLabel("Position"), self.position_slider)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.layout().addLayout(form_layout, 3, 0, 1, 2)
        
        self.register_button = QPushButton("Apply transform")
        self.register_button.clicked.connect(self._on_click_register)
        self.layout().addWidget(self.register_button, 4, 0, 1, 2)

        self.parentWidget().parentWidget().select_images.moving_combo_box.currentTextChanged.connect(self._on_select_moving_image)
        
    @property
    def moving_image_layer(self):
        return self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()
        
    def _on_click_save_ome_zarr(self):
        if self.rotated_layer is None:
            QMessageBox.warning(self, "Error saving image", "Apply transformation before saving as OME-Zarr.")
            return
        save_path = self._get_save_path()
        if save_path is not None:
            # try:
            if isinstance(self.rotated_layer.data, np.ndarray):
                image_pyramid = create_image_pyramid(self.rotated_layer.data)
                shapes = [image.shape for image in image_pyramid]
                scales = get_pyramid_scales(self.rotated_layer.scale, shapes)
                save_ome_zarr(save_path,
                              image_pyramid,
                              chunksize=256,
                              name=self.moving_image_layer.name,
                              scales=scales)
            else:
                scales = get_pyramid_scales(self.rotated_layer.scale, self.rotated_layer.data.shapes)
                save_ome_zarr(save_path, 
                              self.rotated_layer.data,
                              chunksize=self.moving_image_layer.data[0].chunksize,
                              name=self.moving_image_layer.name, 
                              scales=scales)
            QMessageBox.information(self, "Success", f"Image saved successfully")
            # except Exception as e:
            #     QMessageBox.critical(self, "Error", f"Failed to save image: {e}")
    
    def _on_click_save_transform(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, 
                                                   "Save File", 
                                                   "", 
                                                   "Text Files (*.txt);;All Files (*)", 
                                                   options=options)
        if file_path:
            try:
                rotation_matrix = rotation_matrix_from_zy_zx_angles(self.zy_degrees_slider.value(), self.zx_degrees_slider.value())
                np.savetxt(file_path, rotation_matrix, delimiter=',')
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
        
    def _on_click_upload_transform(self):
        if not self.moving_image_layer:
            QMessageBox.critical(self, "Error", "No moving image layer selected")
            return
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, 
                                                   "Open File", 
                                                   "", 
                                                   "Text Files (*.txt);;All Files (*)", 
                                                   options=options)
        
        if file_path:
            try:
                rotation_matrix = np.loadtxt(file_path, delimiter=',')
                if not is_rotation_matrix(rotation_matrix):
                    raise ValueError("Invalid rotation matrix")
                angle_zy, angle_zx = decompose_rotation_matrix(rotation_matrix)
                self.zy_degrees_slider.setValue(np.degrees(angle_zy))
                self.zx_degrees_slider.setValue(np.degrees(angle_zx))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
            
    def _get_save_path(self):
        options = QFileDialog.Options()
        save_path = QFileDialog.getExistingDirectory(self, 
                                                   "Select Save Location", 
                                                   "", 
                                                   options=options)
        if not save_path:
            return None
        elif not os.path.exists(save_path):
            QMessageBox.warning(self, "Invalid save location", "Selected folder does not exist.")
            return None
        elif len(os.listdir(save_path)):
            QMessageBox.warning(self, "Invalid save location", "Selected folder is not empty.")
            return None
        elif not save_path.endswith('.ome.zarr'):
            QMessageBox.warning(self, "Invalid save location", "Selected folder must end with '.ome.zarr'.")
            return None
        return save_path
        
    def _on_change_angle(self):
        if 'plane' not in self.align_planes_window.viewer.layers:
            return
        normal = self._calculate_normal()
        self.align_planes_window.viewer.layers['plane'].plane.normal = normal
        self.update_position_slider()
        
    def _calculate_normal(self):
        normal = np.asarray([[1], [0], [0]])
        rotation_matrix = rotation_matrix_from_zy_zx_angles(self.zy_degrees_slider.value(), self.zx_degrees_slider.value())
        normal = rotation_matrix[:3, :3] @ normal
        return normal.T[0]

    def update_position_slider(self):
        layer = self.align_planes_window.viewer.layers['plane']
        shape = layer.data.shape if isinstance(layer.data, np.ndarray) else layer.data.shapes[-1]
        points = find_intersections([0, 0, 0], shape, np.array(layer.plane.position), np.array(layer.plane.normal))
        if len(points) != 2:
            return
        self.intersection_points = [points[0], points[1]]
        t = calculate_t(points[0], points[1], np.array(layer.plane.position))
        self.position_slider.setValue(t)
        
    def _on_update_position(self):
        if 'plane' not in self.align_planes_window.viewer.layers:
            return
        layer = self.align_planes_window.viewer.layers['plane']
        
        shape = layer.data.shape if isinstance(layer.data, np.ndarray) else layer.data.shapes[-1]
        if self.intersection_points is None:
            layer.plane.position = (shape[0] / 2, shape[1] / 2, shape[2] / 2)
        elif len(self.intersection_points) != 2:
            return
        else:
            t = self.position_slider.value()
            layer.plane.position = line_parametric_equation(self.intersection_points[0], self.intersection_points[1], t)
        
    def _on_click_show(self):
        moving_layer = self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()
        if not isinstance(moving_layer, Image):
            QMessageBox.warning(self, "Error showing image", "Can only show image layers.")
            return
        if self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer() is None:
            QMessageBox.warning(self, "Error showing image", "Select a moving image first.")
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
        shape = moving_layer.data.shape
        moving_layer_plane.plane.position = moving_layer_plane.data_to_world((shape[0] / 2, shape[1] / 2, shape[2] / 2))
        self.align_planes_window.viewer.add_layer(moving_layer)
        self.align_planes_window.viewer.add_layer(moving_layer_plane)
        self.align_planes_window.show()
        self._on_update_position()
        self._on_change_angle()
        
    def reset_ui(self):
        self.zy_degrees_slider.setValue(0)
        self.zx_degrees_slider.setValue(0)
        self.position_slider.setValue(0.5)
        self.intersection_points = None
        
    def _on_select_moving_image(self):
        self.align_planes_window.close()
        self.align_planes_window.viewer.layers.clear()
        # self.reset_ui()
        
    def _init_align_planes_window(self):
        window = StackViewer(napari.Viewer(show=False))
        window.setParent(self)
        window.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        window.viewer.dims.ndisplay = 3
        return window
        
    def _on_click_register(self):
        normal = self._calculate_normal()
        self.rotated_layer = rotate_layer(self.moving_image_layer, np.asarray([0, 0, 1]), np.asarray(normal[::-1]))
        self.viewer.add_layer(self.rotated_layer)
        
        
def rotate_layer(layer, v1, v2):
    layer_type = 'image' if isinstance(layer, Image) else 'labels'
    interpolator = 'linear' if layer_type == 'image' else 'nearest'
    quaternion = quaternion_from_vectors(v1, v2)
    if isinstance(layer.data, np.ndarray):
        rotated_data = rotate_image_3d_sitk(layer.data, quaternion, interpolator)
    else:
        rotated_data = []
        for pyramid_level in layer.data:
            rotated_data.append(rotate_image_3d_sitk(pyramid_level.compute(), quaternion, interpolator))
    rotated_layer = Layer.create(rotated_data, {'scale': layer.scale, 'name': layer.name + ' (rotated)'}, layer_type)
    return rotated_layer
