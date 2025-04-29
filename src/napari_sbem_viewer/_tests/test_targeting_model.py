import pytest
import numpy as np
import numpy.testing as npt
from napari.layers import Image
from napari_sbem_viewer._models.targeting_model import TargetingModel
from tifffile import imwrite


@pytest.fixture
def targeting_model(mocker):
    mock_layer_model = mocker.MagicMock()
    viewer = mocker.MagicMock()
    return TargetingModel(viewer, mock_layer_model)


def test_targeting_model_init(targeting_model):
    # Test the initialization of the TargetingModel
    assert isinstance(targeting_model, TargetingModel)
    assert targeting_model.layer_model is not None
    assert targeting_model.viewer is not None
    assert targeting_model.editing_enabled is True
    assert targeting_model.annotated_labels is None


def test_add_new_labels_layer(targeting_model):
    targeting_model.layer_model.targeting_layer_original = Image(
        name="test", 
        data=np.zeros((5, 7, 12), dtype=np.uint8),
        scale=(1, 2, 3))
    targeting_model.add_new_labels_layer(2)
    assert targeting_model.annotated_labels.shape == (2, 3, 6)
    targeting_model.layer_model.add_labels_layer.assert_called_once()
    labels_layer = targeting_model.layer_model.add_labels_layer.call_args[0][0]
    assert labels_layer.data.shape == (2, 3, 6)
    npt.assert_array_almost_equal(labels_layer.scale, (2, 4, 6))
    

def test_upload_existing_labels(tmp_path, targeting_model):
    targeting_model.layer_model.targeting_layer_original = Image(
        name="test", 
        data=np.zeros((5, 7, 12), dtype=np.uint8),
        scale=(1, 2, 3))

    # Write dummy tiff file
    dummy_tiff_path = str(tmp_path / "dummy_path.tif")
    imwrite(
        dummy_tiff_path,
        np.ones((10, 10, 10), dtype=np.uint8),
    )
    
    # Load dummy tiff file and check if it is uploaded correctly
    targeting_model.upload_existing_labels(dummy_tiff_path)
    assert targeting_model.annotated_labels.shape == (10, 10, 10)
    targeting_model.layer_model.add_labels_layer.assert_called_once()
    labels_layer = targeting_model.layer_model.add_labels_layer.call_args[0][0]
    assert labels_layer.data.shape == (10, 10, 10)
    npt.assert_array_almost_equal(labels_layer.scale, (0.5, 1.4, 3.6))


def test_enable_disable_editing(targeting_model, mocker):
    targeting_model.editing_updated = mocker.MagicMock()
    targeting_model.enable_editing(True)
    assert targeting_model.editing_enabled is True
    targeting_model.editing_updated.emit.assert_called_once()
    targeting_model.enable_editing(False)
    assert targeting_model.editing_enabled is False
    targeting_model.editing_updated.emit.call_count == 2
    