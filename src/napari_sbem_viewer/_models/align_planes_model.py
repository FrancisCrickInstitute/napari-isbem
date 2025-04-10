from copy import copy

from qtpy.QtCore import QObject, Signal
import numpy as np
from napari.layers import Image
from napari.qt import create_worker

from napari_sbem_viewer._utils.registration_utils import (
    rotation_matrix_from_zy_zx_angles,
    rotation_matrix_from_zy_zx_angles,
    calculate_normal,
    transform_layer,
    is_rotation_matrix
    )


class AlignPlanesModel(QObject):
    rotation_started = Signal()
    rotation_finished = Signal(object)
    rotation_errored = Signal(Exception)
    def __init__(self, viewer, stack_viewer, layer_model):
        super().__init__()
        self.viewer = viewer
        self.align_planes_window = stack_viewer
        self.layer_model = layer_model
        self.layer_model.targeting_layer_added.connect(self._on_add_targeting_layer)
        self.layer_model.targeting_layer_removed.connect(self._on_remove_targeting_layer)
        self.layer_model.labels_layer_added.connect(self._on_add_labels_layer)
        self.align_planes_window.image_layer = None
        self.align_planes_window.plane_layer = None
        self.shape = None
        self.t = None
        self.intersection_points = None
        self.affine_matrix = None
    
    def apply_rotation(self, zy_degrees, zx_degrees):
        transform_matrix = rotation_matrix_from_zy_zx_angles(zy_degrees, zx_degrees)
        self.apply_transform(transform_matrix)
        
    def apply_transform(self, transform_matrix):
        self.rotation_started.emit()
        create_worker(self._rotate_images,
                      transform_matrix,
                      _connect={'returned': lambda res: self._on_finish_apply_rotation(*res), 
                                'errored': self.rotation_errored.emit})
        self.affine_matrix = transform_matrix
        
    def _rotate_images(self, transform_matrix):
        image = transform_layer(self.layer_model.targeting_layer_original, transform_matrix)
        labels = None
        if (self.layer_model.labels_layer is not None and 
            self.layer_model.labels_layer_original is not None):
            labels = transform_layer(self.layer_model.labels_layer_original, transform_matrix)
        return image, labels
    
    def _on_finish_apply_rotation(self, image_layer, labels_layer):
        self.layer_model.targeting_layer.data = image_layer.data
        self.layer_model.targeting_layer.translate = image_layer.translate
        self.layer_model.targeting_layer.scale = image_layer.scale
        if (self.layer_model.labels_layer is not None and 
            labels_layer is not None):
            self.layer_model.labels_layer.data = labels_layer.data
            self.layer_model.labels_layer.scale = labels_layer.scale
            self.layer_model.labels_layer.affine = self.layer_model.targeting_layer.affine
            self.layer_model.labels_layer.translate = self.layer_model.targeting_layer.translate
        self.rotation_finished.emit(self.affine_matrix)
            
    def load_transform(self, affine_matrix):
        if not is_rotation_matrix(affine_matrix):
            print(affine_matrix)
            raise ValueError("Invalid transform matrix. Must be a rotation matrix.")
        self.apply_transform(affine_matrix)
        
    def get_rotation_matrix(self):
        return self.affine_matrix
        
    def _on_add_targeting_layer(self, layer):
        self.reset()
        self.layer_model.targeting_layer.events.affine.connect(self._on_affine_changed)
        
    def _on_remove_targeting_layer(self):
        self.reset()

    def _on_add_labels_layer(self, labels_layer):
        self.layer_model.labels_layer.events.data.connect(self._on_labels_data_changed)
        if self.affine_matrix is not None:
            new_layer = transform_layer(self.layer_model.labels_layer_original, self.affine_matrix)
            self.layer_model.labels_layer.data = new_layer.data
            self.layer_model.labels_layer.scale = new_layer.scale
        if self.layer_model.targeting_layer is not None:
            self.layer_model.labels_layer.affine = self.layer_model.targeting_layer.affine
            self.layer_model.labels_layer.translate = self.layer_model.targeting_layer.translate
        
    def show_align_planes_window(self):
        moving_layer = self.layer_model.targeting_layer
        if not isinstance(moving_layer, Image):
            raise ValueError("Can only show image layers.")
        
        self.layer_model.targeting_layer_original.contrast_limits = self.layer_model.targeting_layer.contrast_limits
        self.align_planes_window.viewer.layers.clear()
        self.align_planes_window.image_layer = copy(self.layer_model.targeting_layer_original)
        self.align_planes_window.image_layer.affine = None
        self.align_planes_window.image_layer.name = 'image'
        self.align_planes_window.image_layer.blending = 'translucent'
        
        self.align_planes_window.plane_layer = copy(self.layer_model.targeting_layer_original)
        self.align_planes_window.plane_layer.affine = None
        self.align_planes_window.plane_layer.blending = 'translucent_no_depth'
        self.align_planes_window.plane_layer.name = 'plane'
        self.align_planes_window.plane_layer.depiction = 'plane'
        self.align_planes_window.plane_layer.colormap = 'cyan'
        data = self.layer_model.targeting_layer_original.data
        self.shape = data if isinstance(data, np.ndarray) else data.shapes[-1]
        self.align_planes_window.plane_layer.plane.position = np.array(self.shape) / 2
        self._calculate_intersection_points()
        
        self.align_planes_window.viewer.add_layer(self.align_planes_window.image_layer)
        self.align_planes_window.viewer.add_layer(self.align_planes_window.plane_layer)
        self.align_planes_window.show()
        
    def reset(self):
        self.align_planes_window.image_layer = None
        self.align_planes_window.plane_layer = None
        self.layer = None
        self.shape = None
        self.t = None
        self.intersection_points = None
        self.align_planes_window.close()
        self.align_planes_window.viewer.layers.clear()
        
    def reset_transform(self):
        self.affine_matrix = None
        self.layer_model.targeting_layer.data = self.layer_model.targeting_layer_original.data
        self.layer_model.targeting_layer.affine = self.layer_model.targeting_layer_original.affine
        self.layer_model.targeting_layer.translate = self.layer_model.targeting_layer_original.translate
        self.layer_model.targeting_layer.scale = self.layer_model.targeting_layer_original.scale
        if self.layer_model.labels_layer is not None:
            self.layer_model.labels_layer.data = self.layer_model.labels_layer_original.data
            self.layer_model.labels_layer.affine = self.layer_model.targeting_layer_original.affine
            self.layer_model.labels_layer.translate = self.layer_model.targeting_layer_original.translate
            self.layer_model.labels_layer.scale = self.layer_model.targeting_layer_original.scale
        self.rotation_finished.emit(self.affine_matrix)

    def update_plane_angle(self, zy_degrees, zx_degrees):
        if self.align_planes_window.plane_layer is None:
            return
        
        normal = calculate_normal(zy_degrees, zx_degrees)
        self.align_planes_window.plane_layer.plane.normal = normal
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
        position = self.align_planes_window.plane_layer.plane.position
        normal = self.align_planes_window.plane_layer.plane.normal
        
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
        num = -np.dot(self.align_planes_window.plane_layer.plane.normal, self.intersection_points[0] - self.align_planes_window.plane_layer.plane.position)
        denom = np.dot(self.align_planes_window.plane_layer.plane.normal, self.intersection_points[1] - self.intersection_points[0])
        t = num / denom
        self.t = t
        
    def update_plane_position(self, t):
        if self.align_planes_window.plane_layer is None:
            return
        new_position = (1 - t) * self.intersection_points[0] + t * self.intersection_points[1]
        self.align_planes_window.plane_layer.plane.position = new_position
        self.t = t
        
    def _on_labels_data_changed(self):
        if self.layer_model.labels_layer and self.affine_matrix is None:
            self.layer_model.labels_layer_original.data = self.layer_model.labels_layer.data
        
    def _on_affine_changed(self):
        if self.layer_model.labels_layer:
            self.layer_model.labels_layer.affine = self.layer_model.targeting_layer.affine
            
            
def find_min_max_corners(normal, p, points):
    distances = np.dot(points - p, normal)
    return distances.min(), distances.max()
