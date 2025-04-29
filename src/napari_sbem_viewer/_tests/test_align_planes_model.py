import pytest
import numpy as np
import numpy.testing as npt
from napari.layers import Image, Labels

from napari_sbem_viewer._models import AlignPlanesModel, StackViewer
from napari_sbem_viewer._utils.registration_utils import calculate_normal


@pytest.fixture
def image_layer():
    return Image(np.random.random((5, 100, 100)), name="im")


@pytest.fixture
def labels_layer():
    return Labels(np.random.randint(0, 255, (5, 100, 100)), name="labels")


@pytest.fixture
def align_planes_model(mocker):
    mock_viewer = mocker.MagicMock()
    mock_stack_viewer = mocker.MagicMock()
    mock_layer_model = mocker.MagicMock()
    align_planes_model = AlignPlanesModel(mock_viewer, mock_stack_viewer, mock_layer_model)
    align_planes_model.layer_model.targeting_layer = Image(np.random.random((5, 100, 100)), name="im")
    align_planes_model.layer_model.targeting_layer_original = Image(np.random.random((5, 100, 100)), name="im")
    align_planes_model.rotation_started = mocker.MagicMock()
    align_planes_model.rotation_errored = mocker.MagicMock()
    align_planes_model.rotation_finished = mocker.MagicMock()
    align_planes_model.layer_model.labels_layer = None
    align_planes_model.layer_model.labels_layer_original = None
    return align_planes_model


@pytest.fixture
def align_planes_model_with_stack_viewer(align_planes_model, make_napari_viewer):
    # align_planes_model.align_planes_window = StackViewer(napari.Viewer(show=False))
    align_planes_model.align_planes_window = StackViewer(make_napari_viewer(show=False))
    return align_planes_model


@pytest.fixture
def align_planes_model_with_labels(align_planes_model):
    align_planes_model.layer_model.labels_layer = Labels(np.random.randint(0, 255, (5, 100, 100)), name="labels")
    align_planes_model.layer_model.labels_layer_original = Labels(np.random.randint(0, 255, (5, 100, 100)), name="labels")
    return align_planes_model


def test_align_planes_model_initialization(align_planes_model):
    # Check if the model is initialized correctly
    assert isinstance(align_planes_model, AlignPlanesModel)
    assert align_planes_model.affine_matrix is None
    assert align_planes_model.shape is None
    assert align_planes_model.t is None
    assert align_planes_model.intersection_points is None
    assert align_planes_model.affine_matrix is None
    

def test_rotate_images(align_planes_model, mocker):
    mock_transform_layer = mocker.patch('napari_sbem_viewer._models.align_planes_model.transform_layer')
    transform_matrix = np.array([[1, 0, 0, 0],
                                 [0, 1, 0, 0],
                                 [0, 0, 1, 0],
                                 [0, 0, 0, 1]])
    align_planes_model.transform_layer = mocker.MagicMock()
    align_planes_model._rotate_images(transform_matrix)
    
    # Check if the transform_layer function was called once
    assert mock_transform_layer.call_count == 1
    
    # Verify the input arguments for each call using assert_called_with
    mock_transform_layer.assert_called_with(align_planes_model.layer_model.targeting_layer_original, transform_matrix)
    
   
def test_rotate_images_with_labels(align_planes_model_with_labels, mocker):
    mock_transform_layer = mocker.patch('napari_sbem_viewer._models.align_planes_model.transform_layer')
    transform_matrix = np.array([[1, 0, 0, 0],
                                 [0, 1, 0, 0],
                                 [0, 0, 1, 0],
                                 [0, 0, 0, 1]])
    align_planes_model_with_labels.layer_model.labels_layer = Labels(np.random.randint(0, 255, (5, 100, 100)), name="labels")
    align_planes_model_with_labels.layer_model.labels_layer_original = Labels(np.random.randint(0, 255, (5, 100, 100)), name="labels")
    align_planes_model_with_labels._rotate_images(transform_matrix)
    
    # Check if the transform_layer function was called twice
    assert mock_transform_layer.call_count == 2
    
    # Verify the input arguments for each call
    assert mock_transform_layer.call_args_list[0][0] == (align_planes_model_with_labels.layer_model.targeting_layer_original, transform_matrix)
    assert mock_transform_layer.call_args_list[1][0] == (align_planes_model_with_labels.layer_model.labels_layer_original, transform_matrix)
  
  
def test_load_transform(align_planes_model, mocker):
    mock_transform_matrix = np.array([[1, 0, 0, 0], 
                                      [0, 1, 0, 0], 
                                      [0, 0, 1, 0],
                                      [0, 0, 0, 1]])
    
    # Mock the apply_transform method
    align_planes_model.apply_transform = mocker.MagicMock()
    align_planes_model.load_transform(mock_transform_matrix)

    # Ensure apply_transform is called with the correct arguments
    align_planes_model.apply_transform.assert_called_once_with(mock_transform_matrix)
        
        
@pytest.mark.parametrize("invalid_matrix", [
    np.array([[1, 0, 0], 
              [0, 1, 0], 
              [0, 0, 1]]),  # Not a 4x4 matrix
    np.array([[1, 0, 0, 0], 
              [0, 1, 0, 0], 
              [0, 0, 1, 0],
              [1, 2, 3, 4]])   # Not a valid rotation matrix
])
def test_load_invalid_transform(align_planes_model, invalid_matrix):
    # Check if ValueError is raised
    with pytest.raises(ValueError, match="Invalid transform matrix. Must be a rotation matrix."):
        align_planes_model.load_transform(invalid_matrix)


def test_apply_transform(align_planes_model, mocker):
    mock_create_worker = mocker.patch('napari_sbem_viewer._models.align_planes_model.create_worker')
    mock_transform_matrix = np.array([[1, 0, 0, 0], 
                                      [0, 1, 0, 0], 
                                      [0, 0, 1, 0],
                                      [0, 0, 0, 1]])
    align_planes_model.apply_transform(mock_transform_matrix)

    # Verify that the correct functions were called
    mock_create_worker.assert_called_once()
    args, kwargs = mock_create_worker.call_args
    assert args[0] == align_planes_model._rotate_images
    npt.assert_array_equal(args[1], mock_transform_matrix)
    assert kwargs['_connect']['errored'] == align_planes_model.rotation_errored.emit
    assert 'returned' in kwargs['_connect']
    npt.assert_array_equal(align_planes_model.affine_matrix, mock_transform_matrix)
    align_planes_model.rotation_started.emit.assert_called_once()
        

def test_finish_rotation(align_planes_model, image_layer):
    align_planes_model._on_finish_apply_rotation(image_layer, None)
    align_planes_model.rotation_finished.emit.assert_called_once()
    npt.assert_array_equal(align_planes_model.layer_model.targeting_layer.data, image_layer.data)
    npt.assert_array_equal(align_planes_model.layer_model.targeting_layer.scale, image_layer.scale)
    npt.assert_array_equal(align_planes_model.layer_model.targeting_layer.translate, image_layer.translate)
    assert align_planes_model.layer_model.labels_layer is None
    assert align_planes_model.layer_model.labels_layer_original is None


def test_finish_rotation_with_labels(align_planes_model_with_labels, image_layer, labels_layer):
    align_planes_model_with_labels._on_finish_apply_rotation(image_layer, labels_layer)
    align_planes_model_with_labels.rotation_finished.emit.assert_called_once()
    npt.assert_array_equal(align_planes_model_with_labels.layer_model.targeting_layer.data, image_layer.data)
    npt.assert_array_equal(align_planes_model_with_labels.layer_model.targeting_layer.scale, image_layer.scale)
    npt.assert_array_equal(align_planes_model_with_labels.layer_model.targeting_layer.translate, image_layer.translate)
    npt.assert_array_equal(align_planes_model_with_labels.layer_model.labels_layer.data, labels_layer.data)
    npt.assert_array_equal(align_planes_model_with_labels.layer_model.labels_layer.scale, labels_layer.scale)
    npt.assert_array_equal(align_planes_model_with_labels.layer_model.labels_layer.translate, labels_layer.translate)


def test_reset_transform(align_planes_model_with_labels):
    # Call the reset method
    align_planes_model_with_labels.reset_transform()

    # Check if the original layers are restored
    npt.assert_array_equal(
        align_planes_model_with_labels.layer_model.targeting_layer.data, 
        align_planes_model_with_labels.layer_model.targeting_layer_original.data)
    npt.assert_array_equal(
        align_planes_model_with_labels.layer_model.labels_layer.data, 
        align_planes_model_with_labels.layer_model.labels_layer_original.data)
    assert align_planes_model_with_labels.affine_matrix is None
    
    
def test_reset(align_planes_model):
    align_planes_model.update_plane_angle(10, 10)
    align_planes_model.update_plane_position(0.8)
    
    # Call the reset method
    align_planes_model.reset()
    assert align_planes_model.affine_matrix is None
    assert align_planes_model.shape is None
    assert align_planes_model.t is None
    assert align_planes_model.intersection_points is None
    
    
@pytest.mark.skip(reason="Error closing mock napari viewer")
def test_update_plane_angle(align_planes_model_with_stack_viewer):
    align_planes_model_with_stack_viewer.show_align_planes_window()
    align_planes_model_with_stack_viewer.update_plane_angle(10, 10)
    npt.assert_array_equal(
        align_planes_model_with_stack_viewer.align_planes_window.plane_layer.plane.normal, 
        calculate_normal(10, 10))
    assert len(align_planes_model_with_stack_viewer.intersection_points) == 2
    npt.assert_allclose(align_planes_model_with_stack_viewer.intersection_points[0], np.array([  5., 100.,   0.]))
    npt.assert_allclose(align_planes_model_with_stack_viewer.intersection_points[1], np.array([  0., 0.,   100.]))
    assert align_planes_model_with_stack_viewer.t == 0.5


def test_update_plane_angle_without_viewer(align_planes_model):
    # should return without doing anything
    align_planes_model.update_plane_angle(10, 10)
    assert align_planes_model.intersection_points is None
    assert align_planes_model.t is None
    
    
@pytest.mark.skip(reason="Error closing mock napari viewer")
def test_update_plane_position(align_planes_model_with_stack_viewer):
    align_planes_model_with_stack_viewer.show_align_planes_window()
    align_planes_model_with_stack_viewer.update_plane_position(0.8)
    # check if align_planes_model.align_planes_window.plane_layer.plane.position == (10, 10)
    npt.assert_allclose(
        align_planes_model_with_stack_viewer.align_planes_window.plane_layer.plane.position,
        np.array([1., 50., 50.]))
    assert align_planes_model_with_stack_viewer.t == 0.8
    
    
def test_update_plane_position_without_viewer(align_planes_model):
    # should return without doing anything
    align_planes_model.update_plane_position(0.8)
    assert align_planes_model.t is None
    