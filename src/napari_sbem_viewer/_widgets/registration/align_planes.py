import napari
from napari.layers import Layer
from napari.layers.base._base_constants import ActionType
from napari.layers.points._points_constants import Mode
from qtpy.QtWidgets import QPushButton, QGridLayout, QLabel, QSpinBox, QWidget, QSlider, QProgressBar
from qtpy.QtCore import Qt
import numpy as np
from napari.qt import QtViewer
from copy import copy
from scipy.spatial.transform import Rotation
import cv2
from scipy.ndimage import affine_transform
import time
import SimpleITK as sitk


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
        
        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self._on_click_register)
        self.layout().addWidget(self.register_button, 4, 0, 1, 2)
        
        # self.progress_bar = QProgressBar(value=0)
        # self.layout().addWidget(self.progress_bar, 5, 0, 1, 2)
        self.layout().setRowStretch(self.layout().rowCount(), 1)
        
        
    def _on_change_angle(self):
        normal = [[1], 
                  [0], 
                  [0]]
        transform_matrix_zy = [
            [np.cos(np.radians(self.zy_degrees_slider.value())), -np.sin(np.radians(self.zy_degrees_slider.value())), 0],
            [np.sin(np.radians(self.zy_degrees_slider.value())), np.cos(np.radians(self.zy_degrees_slider.value())), 0],
            [0, 0, 1]
        ]
        transform_matrix_zx = [
            [np.cos(np.radians(self.zx_degrees_slider.value())), 0, np.sin(np.radians(self.zx_degrees_slider.value()))],
            [0, 1, 0],
            [-np.sin(np.radians(self.zx_degrees_slider.value())), 0, np.cos(np.radians(self.zx_degrees_slider.value()))],
        ]
        normal = np.matmul(transform_matrix_zy, normal)
        normal = np.matmul(transform_matrix_zx, normal)
        self.align_planes_window.viewer.layers['plane'].plane.normal = normal
        
        self.update_position_slider()

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
        normal = self.align_planes_window.viewer.layers['plane'].plane.normal
        axis, angle = axis_angle_from_vectors(np.asarray([1, 0, 0]), np.asarray(normal))
        rotated_layer = rotate_layer(self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer(), angle, axis[::-1])
        self.viewer.add_layer(rotated_layer)
        
        
def rotate_layer(layer, angle, axis):
    rotated_data = []
    for pyramid_level in layer.data[1:]:
        rotated_data.append(rotate_image_3d_sitk(pyramid_level.compute(), angle, axis))
    rotated_layer = Layer.create(rotated_data, {'scale': layer.scale, 'name': layer.name + ' (rotated)'}, 'image')
    return rotated_layer
        
        
def rotate_image_3d_sitk(image, angle, axis):
    image_sitk = sitk.GetImageFromArray(image.astype(np.float32))
    transform = sitk.VersorRigid3DTransform()
    transform.SetRotation(axis, angle)
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


def axis_angle_from_vectors(v1, v2):
    # Calculate the rotation axis
    axis = np.cross(v1, v2)
    axis /= np.linalg.norm(axis)

    # Calculate the angle of rotation
    angle = np.arccos(np.dot(v1, v2))

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
