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
                                                          rotate_layer)
from napari_sbem_viewer._utils.image_utils import save_ome_zarr, create_image_pyramid, get_pyramid_scales


class AlignPlanesModel(QObject):
    rotation_finished = Signal()
    rotation_errored = Signal(Exception)
    def __init__(self, viewer, align_planes_window):
        super().__init__()
        self.viewer = viewer
        self.align_planes_window = align_planes_window
        self.rotated_layer = None
        self.moving_image_layer = None
        self.r_max = None
        self.shape = None
    
    def save_ome_zarr(self, save_path):
        if self.rotated_layer is None:
            raise ValueError("Apply transform before saving as OME-Zarr.")
        
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
    
    def apply_rotation(self, zy_degrees, zx_degrees):
        if self.moving_image_layer is None:
            raise ValueError("No image layer selected.")
        normal = calculate_normal(zy_degrees, zx_degrees)
        create_worker(rotate_layer, 
                      self.moving_image_layer,
                      np.asarray([0, 0, 1]),
                      np.asarray(normal[::-1]),
                      _connect={'returned': self._on_finish_apply_rotation, 
                                'errored': self._on_error_apply_rotation})
    
    def _on_finish_apply_rotation(self, rotated_layer):
        self.rotated_layer = rotated_layer
        self.rotation_finished.emit()
    
    def _on_error_apply_rotation(self, e):
        self.rotation_errored.emit(e)
            
    def load_transform(self, file_path):
        rotation_matrix = np.loadtxt(file_path, delimiter=',')
        if not is_rotation_matrix(rotation_matrix):
            raise ValueError("Invalid rotation matrix")
        angle_zy, angle_zx = decompose_rotation_matrix(rotation_matrix)
        return np.degrees(angle_zy), np.degrees(angle_zx)
        
    def save_transform(self, file_path, zy_degrees, zx_degrees):
        rotation_matrix = rotation_matrix_from_zy_zx_angles(zy_degrees, zx_degrees)
        np.savetxt(file_path, rotation_matrix, delimiter=',')
        
    def show_align_planes_window(self):
        moving_layer = self.moving_image_layer
        if not isinstance(moving_layer, Image):
            raise ValueError("Can only show image layers.")
        
        self.align_planes_window.viewer.layers.clear()
        self.image_layer = copy(moving_layer)
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
        self.r_max = max(self.shape)
        
        self.align_planes_window.viewer.add_layer(self.image_layer)
        self.align_planes_window.viewer.add_layer(self.plane_layer)
        self.align_planes_window.show()
        
    def reset(self):
        self.image_layer = None
        self.plane_layer = None
        self.layer = None
        self.r_max = None
        self.shape = None
        self.align_planes_window.close()
        self.align_planes_window.viewer.layers.clear()

    def update_plane_angle(self, zy_degrees, zx_degrees):
        if self.plane_layer is None:
            return
        
        normal = calculate_normal(zy_degrees, zx_degrees)
        self.plane_layer.plane.normal = normal
        
    def update_plane_position(self, t):
        if self.plane_layer is None:
            return
        normal = self.plane_layer.plane.normal
        normal = normal / np.linalg.norm(normal)
        center = np.asarray(self.shape) / 2
        position = normal * t * self.r_max / 2
        self.plane_layer.plane.position = position + center
            