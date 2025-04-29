import pytest
import numpy as np
import numpy.testing as npt
from napari.layers import Points, Image
from skimage.transform import AffineTransform

from napari_sbem_viewer._models import AffineModel, LayerModel


@pytest.fixture
def affine_model_no_layers(mocker):
    mock_viewer = mocker.Mock()
    # make mock_viewer.layers iterable
    mock_viewer.layers = mocker.MagicMock()
    mock_viewer.layers.__iter__.return_value = iter([])
    layer_model = LayerModel(mock_viewer)
    layer_model.em_layer = None
    layer_model.targeting_layer = None
    affine_model = AffineModel(mock_viewer, layer_model)
    return affine_model


@pytest.fixture
def affine_model_no_viewer(affine_model_no_layers):
    affine_model_no_layers.layer_model.em_layer = Image(data=np.random.rand(10, 10, 10), name='em_layer')
    affine_model_no_layers.layer_model.targeting_layer = Image(data=np.random.rand(8, 12, 10), name='targeting_layer')
    return affine_model_no_layers


@pytest.fixture
def affine_model(affine_model_no_viewer, make_napari_viewer):
    viewer = make_napari_viewer(show=False)
    affine_model_no_viewer.viewer = viewer
    viewer.add_layer(affine_model_no_viewer.layer_model.em_layer)
    viewer.add_layer(affine_model_no_viewer.layer_model.targeting_layer)
    return affine_model_no_viewer


def test_initialization(affine_model_no_viewer):
    # Test the initialization of the AffineModel
    assert isinstance(affine_model_no_viewer, AffineModel)
    assert affine_model_no_viewer.delete_pts == True
    assert affine_model_no_viewer.is_doing_registration == False
    assert affine_model_no_viewer.points_layers == [None, None]


def test_start_stop_registration(affine_model):
    # Test the start_registration method
    affine_model.start_registration()
    
    # Check if registration is started
    assert affine_model.is_doing_registration == True
    assert isinstance(affine_model.points_layers[0], Points)
    assert isinstance(affine_model.points_layers[1], Points)
    
    affine_model.start_registration()
    
    # Check if registration is still started
    assert affine_model.is_doing_registration == True
    assert isinstance(affine_model.points_layers[0], Points)
    assert isinstance(affine_model.points_layers[1], Points)
    
    affine_model.stop_registration()
    
    # Check if registration is stopped
    assert affine_model.is_doing_registration == False
    assert affine_model.points_layers == [None, None]


@pytest.mark.parametrize("flip_z", [True, False])
def test_do_transform(affine_model, flip_z):
    affine_model.do_transform = lambda: affine_model._do_transform(flip_z=flip_z, transform_method=AffineTransform, remove_outliers=False)
    # Test the do_transform method
    affine_model.start_registration()
    
    # Add mock points to the points layers
    affine_model.points_layers[0].data = np.array(
        [[0.200, 304.185, 350.924],
         [0.200, 662.683, 315.579],
         [0.200, 427.892, 835.655]])
    affine_model.points_layers[1].data = np.array(
        [[0.200, 464.180, 456.621],
         [0.200, 905.681, 393.117],
         [0.200, 678.883, 1000.936]])
    
    # Check if the transform is applied correctly
    if flip_z:
        expected_transform = np.array([
            [-1.00000000e+00, 0.00000000e+00, 0.00000000e+00, 4.00000000e-01],
            [0.00000000e+00, 7.99337017e-01, -8.80244996e-02, -2.66574214e+01],
            [0.00000000e+00, 4.54559499e-02, 8.72604046e-01, -6.86250748e+01],
            [0.00000000e+00, 0.00000000e+00, 0.00000000e+00, 1.00000000e+00],
            ])
    else:
        expected_transform = np.array([
            [1.00000000e+00, 0.00000000e+00, 0.00000000e+00, 0.00000000e+00],
            [0.00000000e+00, 7.99337017e-01, -8.80244996e-02, -2.66574214e+01],
            [0.00000000e+00, 4.54559499e-02, 8.72604046e-01, -6.86250748e+01],
            [0.00000000e+00, 0.00000000e+00, 0.00000000e+00, 1.00000000e+00],
            ])
    npt.assert_allclose(affine_model.points_layers[1].affine.affine_matrix, 
                        expected_transform)
    npt.assert_allclose(affine_model.layer_model.targeting_layer.affine.affine_matrix,
                        expected_transform)
    
    
def test_activate_model(affine_model_no_layers):
    class MockSignal:
        def __init__(self):
            self.call_count = 0

        def emit(self):
            self.call_count += 1

    # Mock the activated signal and deactivated signals
    affine_model_no_layers.activated = MockSignal()
    affine_model_no_layers.deactivated = MockSignal()

    # Add only em_layer and check that model is not activated
    affine_model_no_layers.layer_model.add_em_layer(Image(data=np.random.rand(10, 10, 10), name='em_layer'))
    assert affine_model_no_layers.activated.call_count == 0

    # Add targeting_layer and check that model is activated
    affine_model_no_layers.layer_model.add_targeting_layer(Image(data=np.random.rand(8, 12, 10), name='targeting_layer'))
    assert affine_model_no_layers.activated.call_count == 1

    # Remove em_layer and check that model is deactivated
    affine_model_no_layers.layer_model.remove_em_layer()
    assert affine_model_no_layers.deactivated.call_count == 1

    # Add em_layer again and check that model is activated again
    affine_model_no_layers.layer_model.add_em_layer(Image(data=np.random.rand(10, 10, 10), name='em_layer'))
    assert affine_model_no_layers.activated.call_count == 2


def test_load_transform(affine_model_no_viewer):
    # test loading various transforms
    transform = np.array([
            [1.00000000e+00, 0.00000000e+00, 0.00000000e+00, 0.00000000e+00],
            [0.00000000e+00, 7.99337017e-01, -8.80244996e-02, -2.66574214e+01],
            [0.00000000e+00, 4.54559499e-02, 8.72604046e-01, -6.86250748e+01],
            [0.00000000e+00, 0.00000000e+00, 0.00000000e+00, 1.00000000e+00],
            ])
    affine_model_no_viewer.load_transform(transform)
    npt.assert_equal(affine_model_no_viewer.layer_model.targeting_layer.affine.affine_matrix, 
                     transform)


@pytest.mark.parametrize("transform", [
    np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
    ]),
    np.array([
        [1.2, 0.2, 0.3, 4],
        [0.2, 1.2, 1.3, 4],
        [0.3, 0.3, 1.2, 4],
        [0.4, 0.4, 0.4, 1]
    ])
])
def test_load_incorrect_transform(affine_model_no_viewer, transform):
    with pytest.raises(ValueError):
        affine_model_no_viewer.load_transform(transform)
