import numpy as np
import numpy.testing as npt
from napari.layers import Labels

from napari_sbem_viewer._models.roi_data import MaskROI, ROIData, ROIState


def test_roi_data_init():
    roi_data = ROIData()
    assert roi_data.rois == []
    assert roi_data.acquiring_rois == set()
    assert roi_data.remaining_rois == set()
    assert np.array_equal(roi_data._offset, np.asarray([0, 0, 0]))


def test_add_masks_single_label():
    labels_layer = Labels(
        data=np.array(
            [
                [[0, 1], [0, 0]],
                [[0, 0], [0, 0]],
            ]
        )
    )
    labels_layer.affine.affine_matrix = np.eye(4)
    labels_layer.scale = np.array([1, 1, 1])
    labels_layer.translate = np.array([0, 0, 0])
    roi_data = ROIData()
    roi_data.add_masks(labels_layer)

    # Assert the correct number of MaskROI objects are created
    assert len(roi_data.rois) == 1

    # Validate properties of the MaskROI
    roi = roi_data.rois[0]
    assert isinstance(roi, MaskROI)
    assert roi.id == 1
    assert roi.state == ROIState.REMAINING
    assert roi.size is not None
    assert roi.mask is not None
    assert roi.x1 == 0.5
    assert roi.x2 == 1.5
    assert roi.y1 == -0.5
    assert roi.y2 == 0.5
    assert roi.z1 == -0.5
    assert roi.z2 == 0.5


def test_add_masks_single_label_scale_translate():
    labels_layer = Labels(
        data=np.array(
            [
                [[0, 1], [0, 0]],
                [[0, 0], [0, 0]],
            ]
        )
    )
    labels_layer.affine.affine_matrix = np.eye(4)
    labels_layer.scale = np.array([1.5, 1.0, 2.5])
    labels_layer.translate = np.array([2, -3, 4])
    roi_data = ROIData()
    roi_data.add_masks(labels_layer)

    # Assert the correct number of MaskROI objects are created
    assert len(roi_data.rois) == 1

    # Validate properties of the MaskROI
    roi = roi_data.rois[0]
    assert isinstance(roi, MaskROI)
    assert roi.id == 1
    assert roi.state == ROIState.REMAINING
    assert roi.size is not None
    assert roi.mask is not None
    assert roi.x1 == 11.25
    assert roi.x2 == 13.75
    assert roi.y1 == -3.5
    assert roi.y2 == -2.5
    assert roi.z1 == 2.25
    assert roi.z2 == 3.75


def test_add_masks_single_label_scale_translate_affine():
    labels_layer = Labels(
        data=np.array(
            [
                [[0, 1], [0, 0]],
                [[0, 0], [0, 0]],
            ]
        )
    )
    labels_layer.affine.affine_matrix = np.array(
        [
            [-1.0, 0.0, 0.0, 2],
            [0.0, 3.2, 1.6, -3],
            [0.0, -2, 1.3, 4],
            [0.0, 0.0, 0.0, 1],
        ]
    )
    labels_layer.scale = np.array([1.5, 1.0, 2.5])
    labels_layer.translate = np.array([2, -3, 4])
    roi_data = ROIData()
    roi_data.add_masks(labels_layer)

    # Assert the correct number of MaskROI objects are created
    assert len(roi_data.rois) == 1

    # Validate properties of the MaskROI
    roi = roi_data.rois[0]
    assert isinstance(roi, MaskROI)
    assert roi.id == 1
    assert roi.state == ROIState.REMAINING
    assert roi.size is not None
    assert roi.mask is not None
    npt.assert_almost_equal(roi.x1, 23.625)
    npt.assert_almost_equal(roi.x2, 28.875)
    npt.assert_almost_equal(roi.y1, 3.8)
    npt.assert_almost_equal(roi.y2, 11.0)
    npt.assert_almost_equal(roi.z1, -1.75)
    npt.assert_almost_equal(roi.z2, -0.25)


def test_add_masks_single_label_scale_translate_affine_offset():
    labels_layer = Labels(
        data=np.array(
            [
                [[0, 1], [0, 0]],
                [[0, 0], [0, 0]],
            ]
        )
    )
    labels_layer.affine.affine_matrix = np.array(
        [
            [-1.0, 0.0, 0.0, 2],
            [0.0, 3.2, 1.6, -3],
            [0.0, -2, 1.3, 4],
            [0.0, 0.0, 0.0, 1],
        ]
    )
    labels_layer.scale = np.array([1.5, 1.0, 2.5])
    labels_layer.translate = np.array([2, -3, 4])
    roi_data = ROIData()
    roi_data.set_offset([12, -3, 2])
    roi_data.add_masks(labels_layer)

    # Assert the correct number of MaskROI objects are created
    assert len(roi_data.rois) == 1

    # Validate properties of the MaskROI
    roi = roi_data.rois[0]
    assert isinstance(roi, MaskROI)
    assert roi.id == 1
    assert roi.state == ROIState.REMAINING
    assert roi.size is not None
    assert roi.mask is not None
    npt.assert_almost_equal(roi.x1, 23.625 + 2)
    npt.assert_almost_equal(roi.x2, 28.875 + 2)
    npt.assert_almost_equal(roi.y1, 3.8 - 3)
    npt.assert_almost_equal(roi.y2, 11.0 - 3)
    npt.assert_almost_equal(roi.z1, -1.75 + 12)
    npt.assert_almost_equal(roi.z2, -0.25 + 12)


def test_add_masks_multi_label():
    labels_layer = Labels(
        data=np.array(
            [
                [[0, 1], [0, 2]],
                [[0, 0], [2, 0]],
            ]
        )
    )
    labels_layer.affine.affine_matrix = np.eye(4)
    labels_layer.scale = np.array([1, 1, 1])
    labels_layer.translate = np.array([0, 0, 0])
    roi_data = ROIData()
    roi_data.add_masks(labels_layer)

    # Assert the correct number of MaskROI objects are created
    assert len(roi_data.rois) == 2

    # Validate properties of the MaskROIs
    roi = roi_data.rois[0]
    assert isinstance(roi, MaskROI)
    assert roi.id == 1
    assert roi.state == ROIState.REMAINING
    assert roi.size is not None
    assert roi.mask is not None
    assert roi.x1 == 0.5
    assert roi.x2 == 1.5
    assert roi.y1 == -0.5
    assert roi.y2 == 0.5
    assert roi.z1 == -0.5
    assert roi.z2 == 0.5

    roi = roi_data.rois[1]
    assert isinstance(roi, MaskROI)
    assert roi.id == 2
    assert roi.state == ROIState.REMAINING
    assert roi.size is not None
    assert roi.mask is not None
    assert roi.x1 == -0.5
    assert roi.x2 == 1.5
    assert roi.y1 == 0.5
    assert roi.y2 == 1.5
    assert roi.z1 == -0.5
    assert roi.z2 == 1.5


def test_add_masks_multi_label_scale_translate():
    labels_layer = Labels(
        data=np.array(
            [
                [[0, 1], [0, 2]],
                [[0, 0], [2, 0]],
            ]
        )
    )
    labels_layer.affine.affine_matrix = np.eye(4)
    labels_layer.scale = np.array([1.5, 1.0, 2.5])
    labels_layer.translate = np.array([2, -3, 4])
    roi_data = ROIData()
    roi_data.add_masks(labels_layer)

    # Assert the correct number of MaskROI objects are created
    assert len(roi_data.rois) == 2

    # Validate properties of the MaskROIs
    roi = roi_data.rois[0]
    assert isinstance(roi, MaskROI)
    assert roi.id == 1
    assert roi.state == ROIState.REMAINING
    assert roi.size is not None
    assert roi.mask is not None
    assert roi.x1 == 11.25
    assert roi.x2 == 13.75
    assert roi.y1 == -3.5
    assert roi.y2 == -2.5
    assert roi.z1 == 2.25
    assert roi.z2 == 3.75

    roi = roi_data.rois[1]
    assert isinstance(roi, MaskROI)
    assert roi.id == 2
    assert roi.state == ROIState.REMAINING
    assert roi.size is not None
    assert roi.mask is not None
    assert roi.x1 == 8.75
    assert roi.x2 == 13.75
    assert roi.y1 == -2.5
    assert roi.y2 == -1.5
    assert roi.z1 == 2.25
    assert roi.z2 == 5.25


def test_add_masks_multi_label_scale_translate_affine():
    labels_layer = Labels(
        data=np.array(
            [
                [[0, 1], [0, 2]],
                [[0, 0], [2, 0]],
            ]
        )
    )
    labels_layer.affine.affine_matrix = np.array(
        [
            [-1.0, 0.0, 0.0, 2],
            [0.0, 3.2, 1.6, -3],
            [0.0, -2, 1.3, 4],
            [0.0, 0.0, 0.0, 1],
        ]
    )
    labels_layer.scale = np.array([1.5, 1.0, 2.5])
    labels_layer.translate = np.array([2, -3, 4])
    roi_data = ROIData()
    roi_data.add_masks(labels_layer)

    # Assert the correct number of MaskROI objects are created
    assert len(roi_data.rois) == 2

    roi = roi_data.rois[0]
    assert isinstance(roi, MaskROI)
    assert roi.id == 2
    assert roi.state == ROIState.REMAINING
    assert roi.size is not None
    assert roi.mask is not None
    npt.assert_almost_equal(roi.x1, 18.375)
    npt.assert_almost_equal(roi.x2, 26.875)
    npt.assert_almost_equal(roi.y1, 3.0)
    npt.assert_almost_equal(roi.y2, 14.2)
    npt.assert_almost_equal(roi.z1, -3.25)
    npt.assert_almost_equal(roi.z2, -0.25)

    # Validate properties of the MaskROIs
    roi = roi_data.rois[1]
    assert isinstance(roi, MaskROI)
    assert roi.id == 1
    assert roi.state == ROIState.REMAINING
    assert roi.size is not None
    assert roi.mask is not None
    npt.assert_almost_equal(roi.x1, 23.625)
    npt.assert_almost_equal(roi.x2, 28.875)
    npt.assert_almost_equal(roi.y1, 3.8)
    npt.assert_almost_equal(roi.y2, 11.0)
    npt.assert_almost_equal(roi.z1, -1.75)
    npt.assert_almost_equal(roi.z2, -0.25)
