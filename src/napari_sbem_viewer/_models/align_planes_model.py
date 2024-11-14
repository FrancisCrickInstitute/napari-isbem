from copy import copy

from qtpy.QtCore import QObject
import numpy as np
from napari.layers import Image, Layer

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


class AlignPlanesModel(QObject):
    def __init__(self, viewer, align_planes_window):
        super().__init__()
        self.viewer = viewer
        self.align_planes_window = align_planes_window
        self.intersection_points = None
        self.rotated_layer = None
    
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
    
    def apply_transform(self):
        normal = self._calculate_normal()
        self.rotated_layer = rotate_layer(self.moving_image_layer, np.asarray([0, 0, 1]), np.asarray(normal[::-1]))
        self.viewer.add_layer(self.rotated_layer)  
            
    def upload_transform(self, file_path):
        rotation_matrix = np.loadtxt(file_path, delimiter=',')
        if not is_rotation_matrix(rotation_matrix):
            raise ValueError("Invalid rotation matrix")
        angle_zy, angle_zx = decompose_rotation_matrix(rotation_matrix)
        self.zy_degrees_slider.setValue(np.degrees(angle_zy))
        self.zx_degrees_slider.setValue(np.degrees(angle_zx))
        
    def save_transform(self, file_path):
        rotation_matrix = rotation_matrix_from_zy_zx_angles(self.zy_degrees_slider.value(), self.zx_degrees_slider.value())
        np.savetxt(file_path, rotation_matrix, delimiter=',')
        
    def show_align_planes_window(self):
        moving_layer = self.moving_image_layer
        if not isinstance(moving_layer, Image):
            raise ValueError("Can only show image layers.")
        
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
        
    def reset(self):
        self.intersection_points = None
        self.rotated_layer = None
        self.align_planes_window.close()
        self.align_planes_window.viewer.layers.clear()
        
    def get_position_value(self):
        layer = self.align_planes_window.viewer.layers['plane']
        shape = layer.data.shape if isinstance(layer.data, np.ndarray) else layer.data.shapes[-1]
        points = find_intersections([0, 0, 0], shape, np.array(layer.plane.position), np.array(layer.plane.normal))
        if len(points) != 2:
            return
        self.intersection_points = [points[0], points[1]]
        t = calculate_t(points[0], points[1], np.array(layer.plane.position))
        return t

    def update_plane_angle(self, zy_degrees, zx_degrees):
        if 'plane' not in self.align_planes_window.viewer.layers:
            return
        normal = calculate_normal(zy_degrees, zx_degrees)
        self.align_planes_window.viewer.layers['plane'].plane.normal = normal
        return self.get_position_value()
        
    def update_plane_position(self, t):
        if 'plane' not in self.align_planes_window.viewer.layers:
            return
        layer = self.align_planes_window.viewer.layers['plane']
        
        shape = layer.data.shape if isinstance(layer.data, np.ndarray) else layer.data.shapes[-1]
        if self.intersection_points is None:
            layer.plane.position = (shape[0] / 2, shape[1] / 2, shape[2] / 2)
        elif len(self.intersection_points) != 2:
            return
        else:
            layer.plane.position = line_parametric_equation(self.intersection_points[0], self.intersection_points[1], t)
            
            
def calculate_normal(zy_degrees, zx_degrees):
    normal = np.asarray([[1], [0], [0]])
    rotation_matrix = rotation_matrix_from_zy_zx_angles(zy_degrees, zx_degrees)
    normal = rotation_matrix[:3, :3] @ normal
    return normal.T[0]


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
