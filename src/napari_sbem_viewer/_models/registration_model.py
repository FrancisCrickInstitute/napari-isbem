from qtpy.QtCore import QObject, Signal
from napari.layers import Layer
import numpy as np

from napari_sbem_viewer._models import AffineModel, AlignPlanesModel
from napari_sbem_viewer._utils.registration_utils import is_2d_affine_matrix, decompose_transform


class RegistrationModel(QObject):
    def __init__(self, viewer, stack_viewer, layer_model):
        super().__init__()
        self.viewer = viewer
        self.layer_model = layer_model
        self.align_planes_model = AlignPlanesModel(self.viewer, stack_viewer)
        self.affine_model = AffineModel(self.viewer)
        self.layer_model.targeting_layer_added.connect(self.set_moving_layer)
        self.layer_model.targeting_layer_removed.connect(self.remove_fixed_layer)
        self.layer_model.em_layer_added.connect(self.set_fixed_layer)
        self.layer_model.em_layer_removed.connect(self.remove_fixed_layer)
        self.layer_model.labels_layer_added.connect(self.align_planes_model.set_labels_layer)
        self.layer_model.labels_layer_removed.connect(self.align_planes_model.remove_labels_layer)
        
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
        if rotation_matrix is None:
            rotation_matrix = np.eye(4)
        transform_matrix = affine_matrix_2d @ rotation_matrix
        np.savetxt(file_path, transform_matrix, delimiter=',')
        
    def set_fixed_layer(self, layer):
        self.affine_model.set_fixed_layer(layer)
        
    def remove_fixed_layer(self):
        self.affine_model.remove_fixed_layer()
        
    def set_moving_layer(self, layer):
        self.align_planes_model.set_moving_layer(layer)
        self.affine_model.set_moving_layer(layer)
        
    def remove_moving_layer(self):
        self.align_planes_model.reset()
        self.affine_model.remove_moving_layer()
        
    def reset_transforms(self):
        self.align_planes_model.reset_transform()
        self.affine_model.reset_transform()
        