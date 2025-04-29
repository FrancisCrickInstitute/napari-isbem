import numpy as np
from qtpy.QtCore import QObject

from napari_sbem_viewer._models import AffineModel, AlignPlanesModel
from napari_sbem_viewer._utils.registration_utils import (
    decompose_transform,
    is_2d_affine_matrix,
)


class RegistrationModel(QObject):
    def __init__(self, viewer, stack_viewer, layer_model):
        super().__init__()
        self.viewer = viewer
        self.layer_model = layer_model
        self.align_planes_model = AlignPlanesModel(
            self.viewer, stack_viewer, layer_model
        )
        self.affine_model = AffineModel(self.viewer, layer_model)

    def load_transform(self, file_path):
        transform_matrix = np.loadtxt(file_path, delimiter=',')

        if transform_matrix.shape != (4, 4):
            raise ValueError('Transform matrix must be 4x4')

        # If transform only includes 2D affine component, load it into the affine model
        if is_2d_affine_matrix(transform_matrix):
            self.affine_model.load_transform(transform_matrix)
            return

        # If transform includes a rotation, decompose it into rotation and affine components
        rot_matrix, affine_matrix_2d = decompose_transform(transform_matrix)
        self.affine_model.load_transform(affine_matrix_2d)
        self.align_planes_model.load_transform(rot_matrix)

    def save_transform(self, file_path):
        rotation_matrix = self.align_planes_model.get_rotation_matrix()
        affine_matrix_2d = self.affine_model.get_affine_matrix()
        if rotation_matrix is None:
            rotation_matrix = np.eye(4)
        transform_matrix = affine_matrix_2d @ rotation_matrix
        np.savetxt(file_path, transform_matrix, delimiter=',')

    def reset_transforms(self):
        self.align_planes_model.reset_transform()
        self.affine_model.reset_transform()
