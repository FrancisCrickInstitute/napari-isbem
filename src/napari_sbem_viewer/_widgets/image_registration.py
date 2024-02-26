import napari
from napari.qt import thread_worker, create_worker
from qtpy.QtWidgets import QPushButton, QVBoxLayout, QWidget, QGroupBox, QVBoxLayout, QMessageBox
import numpy as np
import cv2
from tqdm import tqdm

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
        
    def _on_select_moving_image(self):
        self.manual_registration.moving_points_widget.stack_viewer.image_layer = self.select_images.get_moving_layer()
        
    def _on_select_fixed_image(self):
        self.manual_registration.fixed_points_widget.stack_viewer.image_layer = self.select_images.get_fixed_layer()
        
    def _on_click_manual_register(self):
        self.manual_registration.register_button.setEnabled(False)
        moving_layer = self.select_images.get_moving_layer()
        fixed_layer = self.select_images.get_fixed_layer()
        if moving_layer is None or fixed_layer is None:
            raise ValueError("Select a moving image and a fixed image")
        
        reverse = self.manual_registration.reverse_checkbox.isChecked()
        
        fixed_slice = self.manual_registration.fixed_z_slice_spinbox.value()
        moving_slice = self.manual_registration.moving_z_slice_spinbox.value()
            
        # get the points for the affine transform if they exist
        pts_moving = self.manual_registration.get_moving_points()
        pts_fixed = self.manual_registration.get_fixed_points()
        
        worker = create_worker(do_manual_transform, fixed_layer, moving_layer, fixed_slice, moving_slice, reverse, pts_fixed, pts_moving)
        worker.yielded.connect(self.manual_registration.progress_bar.setValue)
        worker.returned.connect(self._on_transform_image_finished)
        worker.errored.connect(self._reset_ui)
        worker.start()
            
    def _on_transform_image_finished(self, args):
        aligned_image, moving_layer_name, aligned_image_scale = args
        
        self.manual_registration.progress_bar.setValue(100)
        
        # remove the aligned image if it already exists
        new_layer_name = moving_layer_name + " (aligned)" if "(aligned)" not in moving_layer_name else moving_layer_name
        if self._get_layer(new_layer_name) is not None:
            self.viewer.layers.remove(new_layer_name)
            
        # add the aligned image to the viewer
        self.viewer.add_image(aligned_image, name=new_layer_name, scale=aligned_image_scale)
        self._reset_ui()
        
    def _reset_ui(self):
        self.manual_registration.progress_bar.setValue(0)
        self.manual_registration.register_button.setEnabled(True)

    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
    
    
def transform_slice(image, transformation_matrix, shape=None):
    if shape is None:
        shape = image.shape
    return cv2.warpAffine(image, transformation_matrix, (shape[1], shape[0]))


def get_transformation_matrix_2d(moving_points, fixed_points):
    # convert coordinates from (y, x) to (x, y)
    fixed_points = fixed_points[:, ::-1]
    moving_points = moving_points[:, ::-1]
    Rt, _ = cv2.estimateAffinePartial2D(moving_points, fixed_points)
    return Rt

    
def offset_stack(moving_image, moving_slice, fixed_slice, reverse):
    if reverse:
        moving_slice = moving_image.shape[0] - moving_slice
    offset = int(moving_slice - fixed_slice)
        
    if abs(offset) >= moving_image.shape[0]:
        QMessageBox("Invalid offset", "The offset is larger than the moving image z")
        
    if offset > 0:
        # crop the moving image to match the fixed image z 
        offset_image = moving_image[offset:]
    elif offset < 0:
        offset = abs(offset)
        # pad the moving image to match the fixed image z
        offset_image = np.append(
            np.zeros((offset, *moving_image.shape[1:])), 
            moving_image, 
            axis=0)
    return offset_image
                
    
def do_manual_transform(fixed_layer, moving_layer, fixed_slice, moving_slice, reverse, pts_fixed, pts_moving):
    moving_image = moving_layer.data
    aligned_image_scale = moving_layer.scale
    if reverse:
        moving_image = moving_image[::-1]
    if moving_slice is not None and fixed_slice is not None:
        moving_image = offset_stack(moving_image, moving_slice, fixed_slice, reverse)
    if pts_fixed is not None and pts_moving is not None:
        if len(pts_fixed) < 3 and len(pts_moving) < 3:
            QMessageBox.warning("Not enough points", "Select at least 3 points for the transformation")
        if len(pts_fixed) != len(pts_moving):
            raise ValueError("Number of fixed and moving points must be equal")
                
        pts_moving_scaled = pts_moving / np.array(moving_layer.scale[1:])
        pts_fixed_scaled = pts_fixed / np.array(fixed_layer.scale[1:])
        transformation_matrix = get_transformation_matrix_2d(pts_moving_scaled, pts_fixed_scaled)
        aligned_y = max(moving_layer.data.shape[1], fixed_layer.data.shape[1])
        aligned_x = max(moving_layer.data.shape[2], fixed_layer.data.shape[2])
        aligned_image_shape = (moving_image.shape[0], aligned_y, aligned_x)
        
        moving_image_ = np.zeros(aligned_image_shape, moving_image.dtype)

        for i in tqdm(range(aligned_image_shape[0])):
            transformed_slice = transform_slice(moving_image[i], transformation_matrix, aligned_image_shape[1:])
            moving_image_[i, :transformed_slice.shape[0], :transformed_slice.shape[1]] = transformed_slice
            yield int(i / aligned_image_shape[0] * 100)
        moving_image = moving_image_
        aligned_image_scale = (moving_layer.scale[0], 1, 1)
        
    return (moving_image, moving_layer.name, aligned_image_scale)
