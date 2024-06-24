import os
import time

import napari
from napari.layers import Layer
from qtpy.QtWidgets import QPushButton, QGridLayout, QLabel, QSpinBox, QWidget, QSlider, QProgressBar, QFileDialog, QLineEdit, QLabel, QMessageBox
from qtpy.QtCore import Qt
import numpy as np
from napari.qt import QtViewer
from copy import copy
from scipy.spatial.transform import Rotation
from scipy.ndimage import affine_transform
import SimpleITK as sitk
import zarr
import cv2
from ome_zarr.io import parse_url
from ome_zarr.writer import write_multiscale
import napari_ome_zarr
from skimage.transform import downscale_local_mean

from napari_sbem_viewer.utils import log_memory_usage
from napari_sbem_viewer._widgets.registration import SelectDir


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
        self._init_align_planes_window()

        moving_layer = self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()
        if self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer() is None:
            return
        
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
        self.update_position_slider()
        self.align_planes_window.show()
        
    def _init_align_planes_window(self):
        # TODO: only open if not already open
        self.align_planes_window = QtViewer(napari.Viewer(show=False))
        self.align_planes_window.setParent(self)
        self.align_planes_window.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.align_planes_window.viewer.dims.ndisplay = 3
        
    def _on_click_register(self):
        normal = self._calculate_normal()
        image_layer = self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()
        rotated_layer = rotate_layer(image_layer, np.asarray([0, 0, 1]), np.asarray(normal[::-1]))
        self.viewer.add_layer(rotated_layer)
        

def create_ome_metadata(name, scale):
    metadata = {"name": name,
                "axes": [
                    {
                    "name": "z",
                    "type": "space",
                    "unit": "micrometer"
                    },
                    {
                    "name": "y",
                    "type": "space",
                    "unit": "micrometer"
                    },
                    {
                    "name": "x",
                    "type": "space",
                    "unit": "micrometer"
                    }
                ], 
                "datasets": []}
    scale = [1/scale[-1], 1/scale[-2], 1/scale[-3]]
    for i in range(3):
        dataset_metadata = {"path": f"{i}", 
                            "coordinateTransformations": [{"type": "scale",
                                                            "scale": [scale[0], scale[1], scale[2]]}]}
        scale[0], scale[1], scale[2] = scale[1] * 2, scale[2] * 2, scale[0] * 2
        metadata["datasets"].append(dataset_metadata)
    return [metadata]
        
        
def rotate_layer(layer, v1, v2):
    quaternion = quaternion_from_vectors(v1, v2)
    rotated_data = []
    for pyramid_level in layer.data:
        rotated_data.append(rotate_image_3d_sitk(pyramid_level.compute(), quaternion))
    rotated_layer = Layer.create(rotated_data, {'scale': layer.scale, 'name': layer.name + ' (rotated)'}, 'image')
    return rotated_layer
        
        
def rotate_image_3d_sitk(image, quaternion):
    image_sitk = sitk.GetImageFromArray(image.astype(np.float32))
    transform = sitk.VersorTransform(list(quaternion))
    image_center = np.array(image_sitk.GetSize()) / 2.0
    transform.SetCenter(image_center)
    image_rotated = sitk.Resample(image_sitk, transform, sitk.sitkLinear, 0.0, image_sitk.GetPixelID())
    return sitk.GetArrayFromImage(image_rotated).astype(image.dtype)


def convert_to_uint8(image):
    # if image.dtype == np.uint8:
    #     image = image
    # elif image.dtype == np.uint16:
    #     image = image
    if image.dtype == np.float32:
        image = (image * 255)
    return image.astype(np.uint8)


def matrix_from_axis_angle(angle, axis):
    """ Compute rotation matrix from axis-angle.
    This is called exponential map or Rodrigues' formula.
    Returns
    -------
    R : array-like, shape (3, 3)
        Rotation matrix
    """
    ux, uy, uz = axis
    c = np.cos(angle)
    s = np.sin(angle)
    ci = 1.0 - c
    R = np.array([[ci * ux * ux + c,
                   ci * ux * uy - uz * s,
                   ci * ux * uz + uy * s],
                  [ci * uy * ux + uz * s,
                   ci * uy * uy + c,
                   ci * uy * uz - ux * s],
                  [ci * uz * ux - uy * s,
                   ci * uz * uy + ux * s,
                   ci * uz * uz + c],
                  ])

    # This is equivalent to
    # R = (np.eye(3) * np.cos(angle) +
    #      (1.0 - np.cos(angle)) * a[:3, np.newaxis].dot(a[np.newaxis, :3]) +
    #      cross_product_matrix(a[:3]) * np.sin(angle))

    return R
        
        
def rotate_image_3d(image, angle, axis):
    # Create rotation object
    rotation = Rotation.from_rotvec(angle * axis)

    # Calculate center of rotation
    center = np.array(image.shape) / 2

    # Calculate translation to ensure the rotated image fits within the original image
    max_translation = np.ceil(np.sqrt(np.sum(center ** 2)))
    translation = max_translation - center


    # Define transformation matrix (rotation + translation)
    transformation_matrix = np.identity(4)
    transformation_matrix[:3, :3] = rotation.as_matrix()
    # transformation_matrix[:3, 3] = translation
    corners = np.array([[0, 0, 0],
                        [0, image.shape[0], 0],
                        [image.shape[1], 0, 0],
                        [0, 0, image.shape[2]],
                        [image.shape[1], image.shape[0], 0],
                        [image.shape[1], 0, image.shape[2]],
                        [0, image.shape[0], image.shape[2]],
                        [image.shape[1], image.shape[0], image.shape[2]]])
    transformed_corners = np.dot(transformation_matrix[:3, :3], corners.T).T + center
    min_corner = np.min(transformed_corners, axis=0)
    max_corner = np.max(transformed_corners, axis=0)
    transformation_matrix[:3, 3] = -min_corner
    output_shape = np.ceil(max_corner - min_corner).astype(int)
    
    # Apply the transformation to the image
    rotated_image = affine_transform(image, transformation_matrix, output_shape=output_shape).astype(image.dtype)
    rotated_image = rotated_image / 65535
    return rotated_image


def create_image_pyramid(image, downsample_factor, pyramid_levels):
    pyramid = [image]
    for i in range(pyramid_levels):
        pyramid.append(downsample_3d_image_sitk(pyramid[i], downsample_factor))
        # pyramid.append(downsample_3d_image(pyramid[i], downsample_factor))
    return pyramid


def downsample_3d_image_sitk(image, downsample_factor):
    if isinstance(downsample_factor, int):
        downsample_factor = (downsample_factor, downsample_factor, downsample_factor)
    elif len(downsample_factor) != 3:
        raise ValueError("downsample_factor must be an int or a tuple of three ints.")

    sitk_image = sitk.GetImageFromArray(image.astype(np.float32))
    original_spacing = sitk_image.GetSpacing()
    new_spacing = [original_spacing[i] * downsample_factor[i] for i in range(3)]
    original_size = sitk_image.GetSize()
    new_size = [int(original_size[i] / downsample_factor[i]) for i in range(3)]

    resample = sitk.ResampleImageFilter()
    resample.SetOutputSpacing(new_spacing)
    resample.SetSize(new_size)
    resample.SetInterpolator(sitk.sitkLinear)
    downsampled_image_sitk = resample.Execute(sitk_image)

    return sitk.GetArrayFromImage(downsampled_image_sitk).astype(image.dtype)


def downsample_3d_image(image, downsample_factor):
    if isinstance(downsample_factor, int):
        downsample_factor = (downsample_factor, downsample_factor, downsample_factor)
    elif len(downsample_factor) != 3:
        raise ValueError("Factor must be an int or a tuple of three ints.")

    downsampled_image = downscale_local_mean(image, factors=downsample_factor)
    return downsampled_image


def quaternion_from_vectors(v1, v2):
    k_cos_theta = np.dot(v1, v2)
    k = np.linalg.norm(v1) * np.linalg.norm(v2)
    return (*np.cross(v1, v2), k + k_cos_theta)


def axis_angle_from_vectors(v1, v2):
    # Calculate the rotation axis
    axis = np.cross(v1, v2)
    axis /= np.linalg.norm(axis)

    # Calculate the angle of rotation
    angle = np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    return axis, angle


def line_parametric_equation(p1, p2, t):
    t = np.clip(t, 0, 1)
    return p1 + t * (p2 - p1)


def calculate_t(p1, p2, p):
    v = p2 - p1
    w = p - p1
    return np.dot(w, v) / np.dot(v, v)
    
    
def find_intersections(b0, b1, p, v):
    intersection_points = []
    for point in [b0, b1]:
        for direction in [[1, 0, 0], [0, 1, 0], [0, 0, 1]]:
            dot_product = np.dot(v, direction)
            distance_to_plane = np.dot(point - p, direction)
            t = distance_to_plane / dot_product
            intersection_point = p + t * v
            # if the intersection point is within the bounds of the plane, add it to the list
            if np.all(b0 <= intersection_point) and np.all(intersection_point <= b1):
                intersection_points.append(intersection_point)
    return intersection_points


def rotation_matrix_from_vectors(vec1, vec2):
    """Compute the rotation matrix to rotate vec1 onto vec2."""
    # Normalize vectors
    vec1 = vec1 / np.linalg.norm(vec1)
    vec2 = vec2 / np.linalg.norm(vec2)

    # Compute the rotation axis
    axis = np.cross(vec1, vec2)
    axis /= np.linalg.norm(axis)

    # Compute the rotation angle (in radians)
    angle = np.arccos(np.dot(vec1, vec2))

    # Compute the rotation matrix
    cos_theta = np.cos(angle)
    sin_theta = np.sin(angle)
    rot_mat = np.array([[cos_theta + axis[0]**2 * (1 - cos_theta), 
                         axis[0] * axis[1] * (1 - cos_theta) - axis[2] * sin_theta,
                         axis[0] * axis[2] * (1 - cos_theta) + axis[1] * sin_theta],
                        [axis[1] * axis[0] * (1 - cos_theta) + axis[2] * sin_theta,
                         cos_theta + axis[1]**2 * (1 - cos_theta),
                         axis[1] * axis[2] * (1 - cos_theta) - axis[0] * sin_theta],
                        [axis[2] * axis[0] * (1 - cos_theta) - axis[1] * sin_theta,
                         axis[2] * axis[1] * (1 - cos_theta) + axis[0] * sin_theta,
                         cos_theta + axis[2]**2 * (1 - cos_theta)]])
    return rot_mat
