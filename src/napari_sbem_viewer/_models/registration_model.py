import numpy as np
from qtpy.QtCore import QObject

from napari_sbem_viewer._models import AffineModel, AlignPlanesModel
from napari_sbem_viewer._utils.registration_utils import (
    decompose_transform,
    is_2d_affine_matrix,
)


class RegistrationModel(QObject):
    """Model for managing registration transforms and coordination between affine and plane alignment.

    This class coordinates the saving, and loading of rotation and affine transforms,,
    delegating to the AlignPlanesModel and AffineModel as appropriate.

    Attributes:
        viewer: The napari viewer instance.
        layer_model: The model managing image and label layers.
        align_planes_model: The model handling plane alignment and rotation transforms.
        affine_model: The model handling 2D affine transforms and Z translations.
    """
    def __init__(self, viewer, stack_viewer, layer_model):
        """Initializes the RegistrationModel.

        Args:
            viewer: The main napari viewer instance.
            stack_viewer: The StackViewer instance for plane alignment.
            layer_model: The model managing image and label layers.
        """
        super().__init__()
        self.viewer = viewer
        self.layer_model = layer_model
        self.align_planes_model = AlignPlanesModel(
            self.viewer, stack_viewer, layer_model
        )
        self.affine_model = AffineModel(self.viewer, layer_model)

    def load_transform(self, file_path):
        """Loads a transform matrix from file and applies it to the models.
        This decomposes the matrix into rotation and 2D affine components
        and applies them to the respective models.

        Args:
            file_path (str): Path to the transform matrix file.

        Raises:
            ValueError: If the loaded matrix is not 4x4.
        """
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
        """Saves the current combined transform matrix to a file.

        Args:
            file_path (str): Path to save the transform matrix.
        """
        rotation_matrix = self.align_planes_model.get_rotation_matrix()
        affine_matrix_2d = self.affine_model.get_affine_matrix()
        if rotation_matrix is None:
            rotation_matrix = np.eye(4)
        transform_matrix = affine_matrix_2d @ rotation_matrix
        np.savetxt(file_path, transform_matrix, delimiter=',')

    def reset_transforms(self):
        """Resets both the affine and rotation transforms to their original state."""
        self.align_planes_model.reset_transform()
        self.affine_model.reset_transform()
