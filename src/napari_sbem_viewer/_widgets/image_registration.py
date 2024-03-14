import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QVBoxLayout, QMessageBox
import numpy as np
import cv2

from napari_sbem_viewer._widgets import UploadXrayStack, ManualRegistration, SelectImages


class ImageRegistration(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        
        self.upload_xray_stack = UploadXrayStack(napari_viewer)
        self.layout().addWidget(self.upload_xray_stack)
        
        self.select_images = SelectImages(self.viewer)
        self.select_images.moving_combo_box.currentTextChanged.connect(self._on_select_moving_image)
        self.select_images.fixed_combo_box.currentTextChanged.connect(self._on_select_fixed_image)
        self.layout().addWidget(self.select_images)
        
        self.manual_registration = ManualRegistration(napari_viewer)
        self.manual_registration.register_button.clicked.connect(self._on_click_manual_register)
        self.layout().addWidget(self.manual_registration)
        
        self.layout().addStretch(1)
        
    def _on_select_moving_image(self):
        self.manual_registration.moving_points_widget.set_image_layer(self.select_images.get_moving_layer())
        
    def _on_select_fixed_image(self):
        self.manual_registration.fixed_points_widget.set_image_layer(self.select_images.get_fixed_layer())
        
    def _on_click_manual_register(self):
        self.manual_registration.register_button.setEnabled(False)
        moving_layer = self.select_images.get_moving_layer()
        fixed_layer = self.select_images.get_fixed_layer()
        if moving_layer is None or fixed_layer is None:
            raise ValueError("Select a moving image and a fixed image")
        
        reverse = self.manual_registration.reverse_checkbox.isChecked()
        
        fixed_slice = self.manual_registration.fixed_z_slice_spinbox.value()
        moving_slice = self.manual_registration.moving_z_slice_spinbox.value()
            
        # calculate the z-offset in physical units
        if reverse:
            # if reversing the z-axis, the moving layer slice becomes z_shape - moving_slice.
            # additionally, after flipping the z-axis, the moving image must be shifted up by z_shape
            # i.e. moving_layer.data.shape[0] - moving_slice - moving_layer.data.shape[0], and so it simplifies to
            z_offset = -moving_slice * moving_layer.scale[0] - fixed_slice * fixed_layer.scale[0]
        else:
            z_offset = moving_slice * moving_layer.scale[0] - fixed_slice * fixed_layer.scale[0]
            
        # get the points for the affine transform if they exist
        pts_moving = self.manual_registration.get_moving_points()
        pts_moving[:, 0] = pts_moving[:, 0] / moving_layer.scale[-1]
        pts_moving[:, 1] = pts_moving[:, 1] / moving_layer.scale[-2]
        
        pts_fixed = self.manual_registration.get_fixed_points()
        pts_fixed[:, 0] = pts_fixed[:, 0] / fixed_layer.scale[-1]
        pts_fixed[:, 1] = pts_fixed[:, 1] / fixed_layer.scale[-2]
        
        if pts_moving is not None and pts_fixed is not None:
            if len(pts_fixed) != len(pts_moving):
                QMessageBox.warning(self, "Invalid points", "Number of fixed and moving points must be equal")
                self._reset_ui()
                return
            if len(pts_fixed) < 3 and len(pts_moving) < 3:
                QMessageBox.warning(self, "Invalid points", "Select at least 3 points for the transformation")
                self._reset_ui()
                return
        
        T = get_transformation_matrix_3d(reverse, z_offset, pts_fixed, pts_moving, scale=(1/moving_layer.scale[-2], 1/moving_layer.scale[-1]))
        moving_layer.affine = T
            
        # reset the z-depth slider
        self.viewer.dims.set_point(0, fixed_layer.data_to_world((fixed_slice, 0, 0))[0])
        
        # enable the register button
        self._reset_ui()
        
    def _reset_ui(self):
        self.manual_registration.register_button.setEnabled(True)
        self.manual_registration.fixed_points_widget.stack_viewer.hide()
        self.manual_registration.moving_points_widget.stack_viewer.hide()

    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None


def get_transformation_matrix_2d(moving_points, fixed_points):
    # convert coordinates from (y, x) to (x, y)
    fixed_points = fixed_points[:, ::-1]
    moving_points = moving_points[:, ::-1]
    Rt, _ = cv2.estimateAffinePartial2D(moving_points, fixed_points)
    Rt = np.vstack([[Rt[0, 0], Rt[0, 1], Rt[1, 2]], 
                    [Rt[1, 0], Rt[1, 1], Rt[0, 2]], 
                    [0, 0, 1]])
    return Rt


def get_transformation_matrix_3d(reverse, z_offset, pts_fixed, pts_moving, scale=None):
    T = np.eye(4)
    
    # scale transformation to offset the x and y scaling
    if scale is not None:
        T[1, 1] = scale[0]
        T[2, 2] = scale[1]
    
    if reverse:
        T[0, 0] *= -1  # flip z-axis
    
    if z_offset != 0:
        T[0, 3] -= z_offset  # shift image to align with fixed image
    
    if pts_fixed is not None and pts_moving is not None:
        T_2d = get_transformation_matrix_2d(pts_moving, pts_fixed)
        rotation = np.arctan2(T_2d[1, 0], T_2d[0, 0])
        scale_x = T_2d[0, 0] / np.cos(rotation)
        scale_y = T_2d[1, 1] / np.cos(rotation)
        translation_x = T_2d[1, 2]
        translation_y = T_2d[0, 2]
        
        rotate_T = np.eye(4)
        rotate_T[1, 1] = np.cos(rotation)
        rotate_T[1, 2] = np.sin(rotation)
        rotate_T[2, 1] = -np.sin(rotation)
        rotate_T[2, 2] = np.cos(rotation)
        
        scale_T = np.eye(4)
        scale_T[1, 1] = scale_y
        scale_T[2, 2] = scale_x
        
        translate_T = np.eye(4)
        translate_T[2, 3] = translation_x
        translate_T[1, 3] = translation_y

        T = np.matmul(scale_T, T)
        T = np.matmul(rotate_T, T)
        T = np.matmul(translate_T, T)
    
    return T
