from qtpy.QtCore import QObject, Signal
from napari.layers import Layer
from napari_ome_zarr import napari_get_reader
from scipy.spatial.transform import Rotation as R
import numpy as np

from napari_sbem_viewer._models import AffineModel, AlignPlanesModel
from napari_sbem_viewer._utils.registration_utils import is_2d_affine_matrix, is_rotation_matrix


class RegistrationModel(QObject):
    moving_layer_added = Signal(Layer)
    moving_layer_removed = Signal()
    def __init__(self, viewer, stack_viewer):
        super().__init__()
        self.viewer = viewer
        self.align_planes_model = AlignPlanesModel(self.viewer, stack_viewer)
        self.affine_model = AffineModel(self.viewer)
        
    def import_targeting_image(self, file_path):
        if not file_path.endswith('.ome.zarr'):
            raise ValueError("Invalid file format. Must be an OME-Zarr file.")
        reader = napari_get_reader(file_path)
        layer = Layer.create(*reader(file_path)[0])
        self.add_moving_image(layer)
        self.viewer.add_layer(layer)
        
    def load_transform(self, file_path):
        transform_matrix = np.loadtxt(file_path, delimiter=',')
        
        # If transform only includes 2D affine component, load it into the affine model
        if is_2d_affine_matrix(transform_matrix):
            self.affine_model.load_transform(transform_matrix)
            return
        
        # If transform includes a rotation, decompose it into rotation and affine components
        rot_matrix, affine_matrix_2d = decompose_transform(transform_matrix)
        self.affine_model.load_transform(affine_matrix_2d)
        self.align_planes_model.load_transform(rot_matrix)
            
    def rotation_finished(self, image_layer, labels_layer):
        self.viewer.layers.remove(self.align_planes_model.moving_layer_transform)
        self.add_moving_image(image_layer)
        self.viewer.add_layer(image_layer)
        if labels_layer is not None:
            self.viewer.layers.remove(self.align_planes_model.labels_layer)
            self.align_planes_model.add_labels_layer(labels_layer, apply_transform=False)
            self.viewer.add_layer(labels_layer)
        
    def save_transform(self, file_path):
        rotation_matrix = self.align_planes_model.get_rotation_matrix()
        affine_matrix_2d = self.affine_model.get_affine_matrix()
        transform_matrix = affine_matrix_2d @ rotation_matrix
        np.savetxt(file_path, transform_matrix, delimiter=',')
        
    def add_fixed_image(self, layer):
        self.affine_model.set_fixed_image(layer)
        
    def remove_fixed_image(self):
        self.affine_model.remove_fixed_image()
        
    def add_moving_image(self, layer):
        self.align_planes_model.set_moving_layer(layer)
        self.affine_model.set_moving_image(layer)
        self.moving_layer_added.emit(self.align_planes_model.moving_layer_original)
        
    def remove_moving_image(self):
        self.align_planes_model.reset()
        self.affine_model.remove_moving_image()
        self.moving_layer_removed.emit()
        
    def reset_transforms(self):
        self.align_planes_model.reset_transform()
        self.affine_model.reset_transform()
        
    def _on_remove_layer(self, event):
        if (event.value == self.affine_model.moving_image_layer or 
            event.value == self.align_planes_model.moving_layer_original):
            self.remove_moving_image()
        if event.value == self.affine_model.fixed_image_layer:
            self.remove_fixed_image()
            
            
def decompose_transform(transform_matrix):
    R_mat = transform_matrix[:3, :3]
    U, _, Vt = np.linalg.svd(R_mat)
    R_mat = U @ Vt
    is_flip_z = np.linalg.det(R_mat) < 0
    if is_flip_z:
        R_mat[:, 0] *= -1
    euler_angles = R.from_matrix(R_mat).as_euler('yzx', degrees=True)
    euler_angles[-1] = 0
    if is_flip_z:
        euler_angles *= -1
    rot_matrix = np.eye(4)
    rot_matrix[:3, :3] = R.from_euler('yzx', euler_angles, degrees=True).as_matrix()
    affine_matrix_2d = transform_matrix @ np.linalg.inv(rot_matrix)
    affine_matrix_2d[np.abs(affine_matrix_2d) < 1e-6] = 0
    affine_matrix_2d[np.abs(affine_matrix_2d - 1) < 1e-6] = 1
    return rot_matrix, affine_matrix_2d
