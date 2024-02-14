import napari
from qtpy.QtWidgets import QPushButton, QVBoxLayout, QWidget, QGroupBox, QVBoxLayout
import numpy as np
import cv2
from tqdm import tqdm

from napari_sbem_viewer._widgets import UploadXrayStack, ManualRegistration, SelectImages


class ImageRegistration(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        
        self.viewer = napari_viewer
        self.viewer.scale_bar.unit = "um"
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
        moving_layer = self.select_images.get_moving_layer()
        fixed_layer = self.select_images.get_fixed_layer()
        if moving_layer is None or fixed_layer is None:
            raise ValueError("Select a moving image and a fixed image")
        
        moving_image = moving_layer.data
        moving_image_shape = moving_image.shape
        fixed_image_shape = fixed_layer.data.shape
        scale = moving_layer.scale
        
        # reverse the moving image if required
        reverse = self.manual_registration.reverse_checkbox.isChecked()
        if reverse:
            moving_image = moving_image[::-1]
        
        # calculate the z-offset needed for the registration
        offset = None
        moving_slice = self.manual_registration.moving_z_slice_spinbox.value()
        fixed_slice = self.manual_registration.fixed_z_slice_spinbox.value()
        
        if moving_slice is not None and fixed_slice is not None:
            if reverse:
                moving_slice = moving_image.shape[0] - moving_slice
            offset = int(moving_slice - fixed_slice)

        # compute the offset for the moving stack
        if offset:
            if abs(offset) >= moving_image.shape[0]:
                assert ValueError("Invalid offset size")
            if offset > 0:
                # crop the moving image to match the fixed image z 
                moving_image = moving_image[offset:]
            elif offset < 0:
                offset = abs(offset)
                # pad the moving image to match the fixed image z
                moving_image = np.append(np.zeros((offset, *moving_image.shape[1:])), moving_image, axis=0)
                
        # get the points for the affine transform if they exist
        pts_moving = self.manual_registration.get_moving_points()
        pts_fixed = self.manual_registration.get_fixed_points()
        
        # do the affine transform on the image stack
        if pts_fixed is not None and pts_moving is not None and len(pts_fixed) > 2 and len(pts_moving) > 2:
            if len(pts_fixed) != len(pts_moving):
                assert ValueError("Number of fixed and moving points must be equal")
                
            pts_moving = pts_moving / np.array(moving_layer.scale[1:])
            pts_fixed = pts_fixed / np.array(fixed_layer.scale[1:])
            transformation_matrix = get_transformation_matrix_2d(pts_moving, pts_fixed)
            aligned_y = max(moving_image_shape[1], fixed_image_shape[1])
            aligned_x = max(moving_image_shape[2], fixed_image_shape[2])
            aligned_image_shape = (moving_image.shape[0], aligned_y, aligned_x)
            moving_image = transform_stack(moving_image, transformation_matrix, aligned_image_shape)
            scale = [moving_layer.scale[0], 1, 1]
            
        # remove the aligned image if it already exists
        new_layer_name = moving_layer.name + " (aligned)" if "(aligned)" not in moving_layer.name else moving_layer.name
        if self._get_layer(new_layer_name) is not None:
            self.viewer.layers.remove(new_layer_name)
            
        # add the aligned image to the viewer
        self.viewer.add_image(moving_image, name=new_layer_name, scale=scale)

    def _get_layer(self, layer_name):
        for layer in self.viewer.layers:
            if layer.name == layer_name:
                return layer
        return None
    
    
def transform_stack(image, transformation_matrix, shape=None):
    if shape is None:
        shape = image.shape
    image_aligned = np.zeros(shape, image.dtype)
    
    for i in tqdm(range(shape[0])):
        transformed_slice = transform_slice(image[i], transformation_matrix, shape[1:])
        image_aligned[i, :transformed_slice.shape[0], :transformed_slice.shape[1]] = transformed_slice
    return image_aligned
    
    
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
