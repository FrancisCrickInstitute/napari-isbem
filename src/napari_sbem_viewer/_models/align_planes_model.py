from copy import copy

from qtpy.QtCore import QObject, Signal
import numpy as np
from napari.layers import Image
from napari.qt import create_worker

from napari_sbem_viewer._utils.registration_utils import (rotation_matrix_from_zy_zx_angles,
                                                          is_rotation_matrix,
                                                          decompose_rotation_matrix,
                                                          rotation_matrix_from_zy_zx_angles,
                                                          calculate_normal,
                                                          rotate_layer_data)


class AlignPlanesModel(QObject):
    rotation_finished = Signal()
    rotation_errored = Signal(Exception)
    activated = Signal()
    deactivated = Signal()
    def __init__(self, viewer, stack_viewer):
        super().__init__()
        self.viewer = viewer
        self.align_planes_window = stack_viewer
        self.moving_image_layer = None
        self.plane_layer = None
        self.shape = None
        self.t = None
        self.intersection_points = None
    
    def apply_rotation(self, zy_degrees, zx_degrees):
        if self.moving_image_layer is None:
            raise ValueError("No moving image selected.")
        normal = calculate_normal(zy_degrees, zx_degrees)
        create_worker(rotate_layer_data, 
                      self.original_data,
                      np.asarray([0, 0, 1]),
                      np.asarray(normal[::-1]),
                      _connect={'returned': self._on_finish_apply_rotation, 
                                'errored': self._on_error_apply_rotation})
    
    def _on_finish_apply_rotation(self, rotated_image):
        self.moving_image_layer.data = rotated_image
        self.rotation_finished.emit()
        
    def reset_rotation(self):
        self.moving_image_layer.data = self.original_data
    
    def _on_error_apply_rotation(self, e):
        self.rotation_errored.emit(e)
            
    def load_transform(self, rotation_matrix):
        if not is_rotation_matrix(rotation_matrix):
            raise ValueError("Invalid rotation matrix")
        angle_zy, angle_zx = decompose_rotation_matrix(rotation_matrix)
        return np.degrees(angle_zy), np.degrees(angle_zx)
        
    def save_transform(self, file_path, zy_degrees, zx_degrees):
        rotation_matrix = rotation_matrix_from_zy_zx_angles(zy_degrees, zx_degrees)
        np.savetxt(file_path, rotation_matrix, delimiter=',')
        
    def set_moving_layer(self, layer):
        self.reset()
        self.moving_image_layer = layer
        self.original_data = layer.data
        self.activated.emit()
        
    def show_align_planes_window(self):
        moving_layer = self.moving_image_layer
        if not isinstance(moving_layer, Image):
            raise ValueError("Can only show image layers.")
        
        self.align_planes_window.viewer.layers.clear()
        self.image_layer = copy(moving_layer)
        self.image_layer.data = self.original_data
        self.image_layer.affine = None
        self.image_layer.name = 'image'
        self.image_layer.blending = 'translucent'
        
        self.plane_layer = copy(moving_layer)
        self.plane_layer.affine = None
        self.plane_layer.blending = 'translucent_no_depth'
        self.plane_layer.name = 'plane'
        self.plane_layer.depiction = 'plane'
        self.plane_layer.colormap = 'cyan'
        self.shape = self.plane_layer.data.shape if isinstance(self.plane_layer.data, np.ndarray) else self.plane_layer.data.shapes[-1]
        self.plane_layer.plane.position = np.array(self.shape) / 2
        self._calculate_intersection_points()
        
        self.align_planes_window.viewer.add_layer(self.image_layer)
        self.align_planes_window.viewer.add_layer(self.plane_layer)
        self.align_planes_window.show()
        
    def reset(self):
        self.image_layer = None
        self.plane_layer = None
        self.layer = None
        self.shape = None
        self.t = None
        self.intersection_points = None
        self.align_planes_window.close()
        self.align_planes_window.viewer.layers.clear()
        self.deactivated.emit()

    def update_plane_angle(self, zy_degrees, zx_degrees):
        if self.plane_layer is None:
            return
        
        normal = calculate_normal(zy_degrees, zx_degrees)
        self.plane_layer.plane.normal = normal
        self._calculate_intersection_points()
        self._calculate_current_position()
        
    def _calculate_intersection_points(self):
        # contruct 3D points for corners of image
        points = np.array(
            [[0, 0, 0], 
             [0, 0, self.shape[2]], 
             [0, self.shape[1], 0], 
             [0, self.shape[1], self.shape[2]],
             [self.shape[0], 0, 0], 
             [self.shape[0], 0, self.shape[2]], 
             [self.shape[0], self.shape[1], 0],
             [self.shape[0], self.shape[1], self.shape[2]],
             ])
        position = self.plane_layer.plane.position
        normal = self.plane_layer.plane.normal
        
        # calculate min distances from the plane to each corner
        distances = np.dot(points - position, normal)
        
        # find the corners that are closest and farthest from the plane
        max_dist = np.max(distances)
        min_dist = np.min(distances)
        min_corners = points[np.where(distances == max_dist)]
        max_corners = points[np.where(distances == min_dist)]
        
        # if there are multiple corners with the same distance, take the average.
        # position slider moves plane between intersection points
        self.intersection_points = [np.mean(min_corners, axis=0), 
                                    np.mean(max_corners, axis=0)]
        
    def _calculate_current_position(self):
        num = -np.dot(self.plane_layer.plane.normal, self.intersection_points[0] - self.plane_layer.plane.position)
        denom = np.dot(self.plane_layer.plane.normal, self.intersection_points[1] - self.intersection_points[0])
        t = num / denom
        self.t = t
        
    def update_plane_position(self, t):
        if self.plane_layer is None:
            return
        new_position = (1 - t) * self.intersection_points[0] + t * self.intersection_points[1]
        self.plane_layer.plane.position = new_position
        self.t = t
            
            
def find_min_max_corners(normal, p, points):
    distances = np.dot(points - p, normal)
    return distances.min(), distances.max()
