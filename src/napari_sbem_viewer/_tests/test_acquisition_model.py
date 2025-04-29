import numpy as np
import pytest

from napari.layers import Labels
from napari_sbem_viewer._models.acquisition_model import AcquisitionModel
from napari_sbem_viewer._models import ROIData, TCPServer, LiveViewer


@pytest.fixture
def acquisition_model(mocker):
    mock_viewer = mocker.MagicMock()
    mock_layer_model = mocker.MagicMock()
    acquisition_model = AcquisitionModel(mock_viewer, mock_layer_model)
    acquisition_model.errored = mocker.MagicMock()
    acquisition_model.acquisition_info_updated = mocker.MagicMock()
    acquisition_model.rois_updated = mocker.MagicMock()
    return acquisition_model


def test_acquisition_model_init(acquisition_model):
    # Test the initialization of the AcquisitionModel
    assert isinstance(acquisition_model, AcquisitionModel)
    assert acquisition_model.fine_thickness is None
    assert acquisition_model.is_cutting_thin is False
    assert acquisition_model.last_z_depth is None
    assert acquisition_model.pause_before_acquire_roi is False
    assert acquisition_model.pause_after_acquire_roi is False
    assert acquisition_model.reset_rois is True
    assert isinstance(acquisition_model.roi_data, ROIData)
    assert isinstance(acquisition_model.tcp_server, TCPServer)
    assert isinstance(acquisition_model.live_viewer, LiveViewer)



def test_process_request_valid(acquisition_model, mocker):
    mock_request = {
        'slice_thickness': 0.1,
        'z_depth': 0.5,
        'paused': True,
    }
    acquisition_model.live_viewer.is_initialized = mocker.MagicMock(return_value=True)
    acquisition_model._check_fine_thickness = mocker.MagicMock()
    acquisition_model._update_rois = mocker.MagicMock()
    acquisition_model._update_cutting_depth = mocker.MagicMock()

    acquisition_model.process_request(mock_request)
    acquisition_model.acquisition_info_updated.emit.assert_called_with(0.5, 0.1, True)
    acquisition_model._check_fine_thickness.assert_called_once()
    acquisition_model._update_rois.assert_called_with(0.5)
    acquisition_model._update_cutting_depth.assert_called_with(0.5)


def test_process_request_error(acquisition_model, mocker):
    mock_request = {
        'slice_thickness': 50,
        'z_depth': 100,
        'paused': False
    }
    acquisition_model.tcp_server = mocker.MagicMock()
    acquisition_model.live_viewer.is_initialized = mocker.MagicMock(return_value=False)
    acquisition_model.process_request(mock_request)
    acquisition_model.errored.emit.assert_called_once_with("Acquisition error", "Select overview directory before using TCP")
    acquisition_model.tcp_server.pause_acquisition.assert_called_once()


def test_set_roi_layer_with_labels(acquisition_model, mocker):
    roi_layer = Labels(name='test_roi_layer', data=np.array([[0, 1], [1, 0]]))
    acquisition_model.roi_data.set_offset = mocker.MagicMock()
    acquisition_model.roi_data.add_masks = mocker.MagicMock()
    acquisition_model.roi_data.update_z_depth = mocker.MagicMock()

    acquisition_model.set_roi_layer(roi_layer)
    acquisition_model.roi_data.set_offset.assert_called_once_with(
        [acquisition_model.live_viewer.position_z, -acquisition_model.live_viewer.size_y // 2, -acquisition_model.live_viewer.size_x // 2]
    )
    acquisition_model.roi_data.add_masks.assert_called_once_with(roi_layer)
    acquisition_model.rois_updated.emit.assert_called_once_with(acquisition_model.roi_data)


def test_set_roi_layer_none(acquisition_model):
    acquisition_model.set_roi_layer(None)

    assert acquisition_model.reset_rois is True
    acquisition_model.rois_updated.emit.assert_called_once_with(acquisition_model.roi_data)


@pytest.mark.parametrize("pixel_size_z, fine_thickness, expected", [
    (0.1, 200, False),
    (0.1, 300, False),
    (0.4, 200, True),
    (0.2, 500, False),
])
def test_check_fine_thickness(acquisition_model, pixel_size_z, fine_thickness, expected):
    acquisition_model.live_viewer.pixel_size_z = pixel_size_z
    acquisition_model.fine_thickness = fine_thickness
    
    if expected:
        acquisition_model._check_fine_thickness()
    else:
        with pytest.raises(ValueError, match="Fine thickness must be a multiple of coarse thickness."):
            acquisition_model._check_fine_thickness()
        

def test_check_fine_thickness_error(acquisition_model):
    acquisition_model.live_viewer.pixel_size_z = 0.1
    acquisition_model.fine_thickness = 0.2
    with pytest.raises(ValueError, match="Fine thickness must be a multiple of coarse thickness."):
        acquisition_model._check_fine_thickness()


def test_reset_view(acquisition_model, mocker):
    acquisition_model.live_viewer.reset_z_view = mocker.MagicMock()
    acquisition_model.reset_view()
    acquisition_model.viewer.reset_view.assert_called_once()
    acquisition_model.live_viewer.reset_z_view.assert_called_once()