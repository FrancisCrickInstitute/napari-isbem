from enum import Enum

import numpy as np
from qtpy.QtCore import QObject
from napari.layers.base._base_constants import Mode, ActionType
from napari.layers import Image
from skimage.transform import (
        AffineTransform,
        EuclideanTransform,
        SimilarityTransform,
        )

from napari_sbem_viewer._utils.registration_utils import (flip_transform_matrix, 
                                                          offset_transform_matrix_z,
                                                          calculate_transform, 
                                                          calculate_z_transform, 
                                                          convert_affine_to_ndims,
                                                          is_2d_affine_matrix)
from napari_sbem_viewer._utils.general_utils import reset_view


class ManualRegistrationModel(QObject):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.delete_pts = True
        self.points_layers = [None, None]
        self.moving_image_layer = None
        self.fixed_image_layer = None
        self.is_doing_registration = False
        
    def start_registration(self):
        if not self.moving_image_layer or not self.fixed_image_layer:
            raise ValueError("No images selected")
        
        if not isinstance(self.moving_image_layer, Image) or not isinstance(self.fixed_image_layer, Image):
            raise ValueError("Both layers must be images")
        
        if self.moving_image_layer == self.fixed_image_layer:
            raise ValueError("Images must be different")
        
        self.moving_image_layer.events.affine.connect(self._affine_callback)
        self._create_points_layers()
        
        pts_layer0 = self.points_layers[0]
        pts_layer1 = self.points_layers[1]
        pts_layer0.events.data.connect(self._on_add_point)
        pts_layer1.events.data.connect(self._on_add_point)

        # get the layer order started
        for layer in [self.fixed_image_layer, pts_layer0, self.moving_image_layer, pts_layer1]:
            self.viewer.layers.move(self.viewer.layers.index(layer), -1)

        self._focus_fixed_layer()
        self.is_doing_registration = True
        
    def stop_registration(self):
        if not self.is_doing_registration:
            return
        self.moving_image_layer.mode = Mode.PAN_ZOOM
        self.moving_image_layer.events.affine.disconnect(self._affine_callback)
        self._remove_points_layers()
        self.is_doing_registration = False
            
    def reset_transform(self):
        self.moving_image_layer.affine = None
        
    def upload_transform(self, file_path):
        if self.moving_image_layer is None:
            raise ValueError("No moving image layer selected")
        transform = np.loadtxt(file_path, delimiter=',')
        if not is_2d_affine_matrix(transform):
            raise ValueError("Transform must be a 2D affine transform")
        self.moving_image_layer.affine = convert_affine_to_ndims(
            transform, 
            self.moving_image_layer.ndim
            )
        
    def save_transform(self, file_path):
        if self.moving_image_layer is None:
            raise ValueError("No moving image layer selected")
        np.savetxt(file_path, np.asarray(self.moving_image_layer.affine.affine_matrix), delimiter=',')
        
    def toggle_manual_adjustment(self):
        if self.moving_image_layer is None and not isinstance(self.moving_image_layer, Image):
            return
        if self.moving_image_layer.mode != Mode.TRANSFORM:
            self.moving_image_layer.mode = Mode.TRANSFORM
            self.viewer.layers.selection.active = self.moving_image_layer
        else:
            self.moving_image_layer.mode = Mode.PAN_ZOOM
            
    def is_moving_image_flipped(self):
        if not self.moving_image_layer:
            return False
        return self.moving_image_layer.affine.affine_matrix[0, 0] < 0
    
    def do_transform(self):
        raise NotImplementedError("do_transform must be implemented in ManualRegistrationController")
        
    def _offset_z(self, offset):
        moving_points_layer = self.points_layers[1]
        if self.moving_image_layer is not None:
            current_z = self.viewer.dims.point[0]
            mat = convert_affine_to_ndims(self.moving_image_layer.affine.affine_matrix, 3)
            offset_transform_matrix_z(mat, offset)
            ref_mat = convert_affine_to_ndims(self.fixed_image_layer.affine.affine_matrix, 3)
            self.moving_image_layer.affine = convert_affine_to_ndims(
                    (ref_mat @ mat), self.moving_image_layer.ndim
                    )
            if moving_points_layer is not None:
                moving_points_layer.affine = convert_affine_to_ndims(
                        (ref_mat @ mat), moving_points_layer.ndim
                        )
            self.viewer.dims.set_point(0,  current_z)
            
    def _flip_z(self):
        moving_points_layer = self.points_layers[1]
        if self.moving_image_layer is not None:
            mat = convert_affine_to_ndims(self.moving_image_layer.affine.affine_matrix, 3) 
            mat = flip_transform_matrix(mat, self.moving_image_layer.data.shape[-3] * self.moving_image_layer.scale[-3])
            self.moving_image_layer.affine = convert_affine_to_ndims(
                    mat, self.moving_image_layer.ndim
                    )           
            if moving_points_layer is not None:
                moving_points_layer.affine = convert_affine_to_ndims(
                        mat, moving_points_layer.ndim
                        )

    def _create_points_layers(self):
        # set points layer for each image
        # Use C0 and C1 from matplotlib color cycle
        points_layers_to_add = [(self.fixed_image_layer, (0.122, 0.467, 0.706, 1.0)),
                                (self.moving_image_layer, (1.0, 0.498, 0.055, 1.0))]

        # make points layer if it was not specified
        estimation_ndim = min(self.fixed_image_layer.ndim, self.moving_image_layer.ndim)
        for i in range(len(self.points_layers)):
            if self.points_layers[i] not in self.viewer.layers:
                layer, color = points_layers_to_add[i]
                new_layer = self.viewer.add_points(
                        ndim=estimation_ndim, # ndims of all points layers same lowest ndim of fixed or moving
                        name=layer.name + '_pts',
                        affine=convert_affine_to_ndims(
                                layer.affine, estimation_ndim
                                ),
                        face_color=[color],
                        )
                self.points_layers[i] = new_layer

    def _focus_fixed_layer(self, reset_camera=True):
        fixed_points_layer = self.points_layers[0]
        self.viewer.layers.selection.active = fixed_points_layer
        self.viewer.layers.move(self.viewer.layers.index(self.fixed_image_layer), -1)
        self.viewer.layers.move(self.viewer.layers.index(fixed_points_layer), -1)
        fixed_points_layer.mode = 'add'
        if reset_camera:
            reset_view(self.viewer, self.fixed_image_layer)
        if len(fixed_points_layer.data):
            z_height = fixed_points_layer.data[-1][0]
            self.viewer.dims._increment_dims_right(0)  # TODO: instead of incrementing, find a way to refresh the viewer without changing the dims
            self.viewer.dims.set_point(0, z_height)
        
    def _focus_moving_layer(self, reset_camera=True):
        moving_points_layer = self.points_layers[1]
        self.viewer.layers.selection.active = moving_points_layer
        self.viewer.layers.move(self.viewer.layers.index(self.moving_image_layer), -1)
        self.viewer.layers.move(self.viewer.layers.index(moving_points_layer), -1)
        moving_points_layer.mode = 'add'
        if reset_camera:
            reset_view(self.viewer, self.moving_image_layer)
            
    def _remove_points_layers(self):
        for layer in self.points_layers:
            self.viewer.layers.remove(layer)
        self.points_layers = [None, None]
        
    def _affine_callback(self):
        moving_points_layer = self.points_layers[1]
        moving_points_layer.affine = convert_affine_to_ndims(
            self.moving_image_layer.affine.affine_matrix, moving_points_layer.ndim
            )
            
    def _do_transform(self, flip_z, transform_method, remove_outliers):
        fixed_points_layer, moving_points_layer = self.points_layers
        if self.fixed_image_layer is None or self.moving_image_layer is None:
            return
        if fixed_points_layer is None or moving_points_layer is None:
            return
        pts0, pts1 = fixed_points_layer.data, moving_points_layer.data
        ndim_raw = pts0.shape[1]  # shape of raw points
        pts0, pts1 = pts0[:, -2:], pts1[:, -2:]  
        ndim = pts0.shape[1]  # shape of points after potentially changing to 2D
        if len(pts0) != len(pts1) or len(pts0) <= ndim:
            return
        mat = calculate_transform(
            pts0, 
            pts1, 
            ndim, 
            model_class=transform_method,
            remove_outliers=remove_outliers
            )
        # if image is 3D, add z-shift to 2D transform
        if ndim_raw > 2:
            z_mat = calculate_z_transform(fixed_points_layer, moving_points_layer, flip_z)
            mat = z_mat @ convert_affine_to_ndims(mat, ndim_raw)
        ref_mat = self.fixed_image_layer.affine.affine_matrix
        # must shrink ndims of affine matrix if dims of image layer is bigger than moving layer
        if self.fixed_image_layer.ndim > self.moving_image_layer.ndim:
            ref_mat = convert_affine_to_ndims(
                    ref_mat, self.moving_image_layer.ndim
                    )
        # must pad affine matrix with identity matrix if dims of moving layer smaller
        self.moving_image_layer.affine = convert_affine_to_ndims(
                (ref_mat @ mat), self.moving_image_layer.ndim
                )
        moving_points_layer.affine = convert_affine_to_ndims(
                (ref_mat @ mat), moving_points_layer.ndim
                )
        
    def _on_add_point(self, event):
        if not event.action == ActionType.ADDED:
            return
        fixed_points_layer, moving_points_layer = self.points_layers
        reset_camera = len(fixed_points_layer.data) < fixed_points_layer.ndim + 1
        if fixed_points_layer in self.viewer.layers.selection:
            self._focus_moving_layer(reset_camera=reset_camera)
        elif moving_points_layer in self.viewer.layers.selection:
            self.do_transform()
            self._focus_fixed_layer(reset_camera=reset_camera)
        
        
class AffineTransformChoices(Enum):
    Affine = AffineTransform
    Euclidean = EuclideanTransform
    Similarity = SimilarityTransform
    