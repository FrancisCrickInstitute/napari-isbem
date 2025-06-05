import numpy as np
import numpy.testing as npt
import pytest

from napari_sbem_viewer._models import (
    AffineModel,
    AlignPlanesModel,
    RegistrationModel,
)
from napari_sbem_viewer._utils.registration_utils import decompose_transform


@pytest.fixture
def registration_model(mocker):
    mock_viewer = mocker.MagicMock()
    mock_stack_viewer = mocker.MagicMock()
    mock_layer_model = mocker.MagicMock()
    registration_model = RegistrationModel(
        mock_viewer, mock_stack_viewer, mock_layer_model
    )

    # Mock the child models
    registration_model.align_planes_model = mocker.MagicMock()
    registration_model.align_planes_model.load_transform = mocker.MagicMock()
    registration_model.affine_model = mocker.MagicMock()
    registration_model.affine_model.load_transform = mocker.MagicMock()

    return registration_model


def test_registration_model_initialization(mocker):
    # Create mock viewer and stack_viewer
    mock_viewer = mocker.MagicMock()
    mock_stack_viewer = mocker.MagicMock()
    mock_layer_model = mocker.MagicMock()

    # Initialize RegistrationModel
    registration_model = RegistrationModel(
        mock_viewer, mock_stack_viewer, mock_layer_model
    )

    # Check if the models are initialized correctly
    assert isinstance(registration_model.align_planes_model, AlignPlanesModel)
    assert isinstance(registration_model.affine_model, AffineModel)


def test_load_identity_transform(registration_model, tmp_path):
    # Create a temporary file using tmp_path
    mock_file_path = str(tmp_path / 'mock_transform.txt')
    mock_identity_matrix = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    # Save the identity matrix to the temporary file
    np.savetxt(mock_file_path, mock_identity_matrix, delimiter=',')

    # Call the load_transform method
    registration_model.load_transform(mock_file_path)

    # Check if the correct methods were called
    registration_model.affine_model.load_transform.assert_called_once()
    registration_model.align_planes_model.load_transform.assert_not_called()
    npt.assert_array_equal(
        registration_model.affine_model.load_transform.call_args[0][0],
        mock_identity_matrix,
    )


def test_load_incorrect_transform_raises_error(registration_model, tmp_path):
    # Mock the file path and incorrect transform matrix
    mock_file_path = str(tmp_path / 'mock_transform.txt')
    mock_transform_matrix = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]
    )  # Incorrect shape
    # Save the identity matrix to the temporary file
    np.savetxt(mock_file_path, mock_transform_matrix, delimiter=',')

    # Check if ValueError is raised
    with pytest.raises(ValueError, match='Transform matrix must be 4x4'):
        registration_model.load_transform(mock_file_path)


def test_load_affine_transform(registration_model, tmp_path):
    # Mock the file path and transform matrix
    mock_file_path = str(tmp_path / 'mock_transform.txt')
    mock_affine_matrix = np.array(
        [[-1, 0, 0, 30], [0, 0.19, -9.2, 80], [0, 2.4, 1.3, 103], [0, 0, 0, 1]]
    )
    # Save the identity matrix to the temporary file
    np.savetxt(mock_file_path, mock_affine_matrix, delimiter=',')

    # Call the load_transform method
    registration_model.load_transform(mock_file_path)

    # Check if the correct methods were called
    registration_model.affine_model.load_transform.assert_called_once()
    registration_model.align_planes_model.load_transform.assert_not_called()
    npt.assert_array_equal(
        registration_model.affine_model.load_transform.call_args[0][0],
        mock_affine_matrix,
    )


def test_load_combined_transform(registration_model, tmp_path):
    # Mock the file path and transform matrix
    mock_file_path = str(tmp_path / 'mock_transform.txt')
    mock_combined_matrix = np.array(
        [
            [-1.000, -0.027, -0.013, 73.900],
            [0.014, -0.000, -1.114, 1128.886],
            [-0.030, 1.102, -0.001, -173.869],
            [0.000, 0.000, 0.000, 1.000],
        ]
    )

    # Save the identity matrix to the temporary file
    np.savetxt(mock_file_path, mock_combined_matrix, delimiter=',')

    # Call the load_transform method
    registration_model.load_transform(mock_file_path)

    # Check if the correct methods were called
    rot_matrix, affine_matrix_2d = decompose_transform(mock_combined_matrix)
    registration_model.affine_model.load_transform.assert_called_once()
    registration_model.align_planes_model.load_transform.assert_called_once()
    npt.assert_array_equal(
        registration_model.align_planes_model.load_transform.call_args[0][0],
        rot_matrix,
    )
    npt.assert_array_equal(
        registration_model.affine_model.load_transform.call_args[0][0],
        affine_matrix_2d,
    )


def test_reset_transforms(registration_model):
    # Call the reset_transforms method
    registration_model.reset_transforms()

    # Check if the reset_transform methods of both models were called
    registration_model.align_planes_model.reset_transform.assert_called_once()
    registration_model.affine_model.reset_transform.assert_called_once()


def test_save_transform(registration_model, tmp_path):
    # Mock the file path and transform matrix
    mock_file_path = str(tmp_path / 'mock_transform.txt')
    mock_rotation_matrix = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    mock_affine_matrix_2d = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )

    # Mock the get_rotation_matrix and get_affine_matrix methods
    registration_model.align_planes_model.get_rotation_matrix.return_value = (
        mock_rotation_matrix
    )
    registration_model.affine_model.get_affine_matrix.return_value = (
        mock_affine_matrix_2d
    )

    # Call the save_transform method
    registration_model.save_transform(mock_file_path)

    # Load the transform matrix
    saved_matrix = np.loadtxt(mock_file_path, delimiter=',')
    expected_transform_matrix = mock_affine_matrix_2d @ mock_rotation_matrix
    npt.assert_array_equal(saved_matrix, expected_transform_matrix)


def test_save_transform_with_none(registration_model, tmp_path):
    # Mock the file path and transform matrix
    mock_file_path = str(tmp_path / 'mock_transform.txt')
    mock_rotation_matrix = None
    mock_affine_matrix_2d = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )

    # Mock the get_rotation_matrix and get_affine_matrix methods
    registration_model.align_planes_model.get_rotation_matrix.return_value = (
        mock_rotation_matrix
    )
    registration_model.affine_model.get_affine_matrix.return_value = (
        mock_affine_matrix_2d
    )

    # Call the save_transform method
    registration_model.save_transform(mock_file_path)

    # Load the transform matrix
    saved_matrix = np.loadtxt(mock_file_path, delimiter=',')
    expected_transform_matrix = mock_affine_matrix_2d
    npt.assert_array_equal(saved_matrix, expected_transform_matrix)
