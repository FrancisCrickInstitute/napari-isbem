import cv2
import numpy as np
import tifffile
from napari.layers import Labels
from napari.qt import create_worker
from qtpy.QtCore import QObject, Signal
from scipy.ndimage import distance_transform_edt

from napari_sbem_viewer._utils.image_utils import (
    connected_components_sitk,
    dilate_with_sphere_sitk,
    merge_nearby_objects,
)


class TargetingModel(QObject):
    interpolation_progress_updated = Signal(int)
    interpolation_started = Signal()
    interpolation_finished = Signal()
    editing_updated = Signal()

    def __init__(self, viewer, layer_model):
        super().__init__()
        self.viewer = viewer
        self.layer_model = layer_model
        self.annotated_labels = None
        self.autofill_labels = False
        self.editing_enabled = True
        self.layer_model.targeting_layer_removed.connect(
            self.layer_model.remove_labels_layer
        )
        self.layer_model.labels_layer_removed.connect(self.reset_labels)

    def add_new_labels_layer(self, downsample_factor):
        labels_shape = [
            dim // downsample_factor
            for dim in self.layer_model.targeting_layer_original.data.shape
        ]
        labels = np.zeros(labels_shape, dtype=np.uint8)
        layer = Labels(
            labels,
            name='ROIs',
            scale=[
                downsample_factor * s
                for s in self.layer_model.targeting_layer_original.scale
            ],
        )
        layer.events.paint.connect(self._on_paint_labels)
        self.annotated_labels = layer.data.copy()
        self.layer_model.add_labels_layer(layer)

    def upload_existing_labels(self, file_path):
        labels = tifffile.imread(file_path)
        scale_factors = calculate_scale(
            labels.shape, self.layer_model.targeting_layer_original.data.shape
        )
        scale = [
            s * f
            for s, f in zip(
                self.layer_model.targeting_layer_original.scale, scale_factors
            )
        ]
        layer = Labels(labels, name='ROIs', scale=scale)
        layer.events.paint.connect(self._on_paint_labels)
        self.annotated_labels = layer.data.copy()
        self.layer_model.add_labels_layer(layer)

    def connected_components(self):
        if self.layer_model.labels_layer is None:
            raise ValueError('No labels layer found')
        cc_mask = connected_components_sitk(self.layer_model.labels_layer.data)
        self.layer_model.labels_layer.data = cc_mask
        self.annotated_labels = cc_mask.copy()

    def merge_nearby_labels(self, tolerance):
        tolerance_px = round(
            tolerance / self.layer_model.labels_layer.scale[0]
        )  # TODO: assumes isotropic scale
        merged_labels = merge_nearby_objects(
            self.layer_model.labels_layer.data > 0, tolerance_px
        )
        self.layer_model.labels_layer.data = merged_labels
        self.annotated_labels = merged_labels.copy()

    def dilate_labels(self, size):
        size_px = round(
            size / self.layer_model.labels_layer.scale[0]
        )  # TODO: assumes isotropic scale
        for label in np.unique(self.layer_model.labels_layer.data):
            if label == 0:
                continue
            mask = self.layer_model.labels_layer.data == label
            dilated_mask = dilate_with_sphere_sitk(mask, size_px)
            self.layer_model.labels_layer.data[dilated_mask] = label
        self.layer_model.labels_layer.data = self.layer_model.labels_layer.data
        self.annotated_labels = self.layer_model.labels_layer.data.copy()

    def interpolate_labels(self):
        if self.annotated_labels is None:
            raise ValueError('No labels layer found')

        self.interpolation_progress_updated.emit(0)
        self.interpolation_started.emit()
        create_worker(
            interpolate_labelled_mask,
            self.annotated_labels.copy(),
            _connect={
                'returned': self._add_interpolated_labels,
                'yielded': self.interpolation_progress_updated.emit,
                'errored': self._on_finish_interpolation,
            },
        )

    def reset_interpolation(self):
        self.interpolation_progress_updated.emit(0)
        self.layer_model.labels_layer.data = self.annotated_labels

    def reset_labels(self):
        self.annotated_labels = None
        self.interpolation_progress_updated.emit(0)
        self.interpolation_finished.emit()

    def enable_editing(self, enabled):
        self.editing_enabled = enabled == True
        self.editing_updated.emit()

    def _on_paint_labels(self, event):
        if not self.editing_enabled:
            return
        if event.type != 'paint':
            return
        layer = event.source
        z_coord = event.value[0][0][0][0]
        label = int(event.value[0][2])
        if label > 0 and self.autofill_labels:
            x_coords = np.array([coord[2][0] for coord, _, _ in event.value])
            y_coords = np.array([coord[1][0] for coord, _, _ in event.value])
            contours = create_contour(x_coords, y_coords)
            cv2.fillPoly(layer.data[z_coord], [contours], color=label)
            layer.data = layer.data
        self.annotated_labels[z_coord] = layer.data[z_coord]

    def _add_interpolated_labels(self, interpolated_labels):
        self.layer_model.labels_layer.data = interpolated_labels
        self._on_finish_interpolation()

    def _on_finish_interpolation(self):
        self.interpolation_finished.emit()


def calculate_scale(source_shape, target_shape):
    return [dim1 / dim2 for dim1, dim2 in zip(target_shape, source_shape)]


def create_contour(x_coords, y_coords):
    """
    Converts x and y coordinate arrays into a contour format suitable for OpenCV.

    Parameters:
        x_coords (numpy.ndarray): Array of x-coordinates.
        y_coords (numpy.ndarray): Array of y-coordinates.

    Returns:
        list: A list containing a single contour (numpy.ndarray of shape Nx1x2).
    """
    # Combine x and y coordinates into a single array of points
    points = np.column_stack((x_coords, y_coords))

    # Reshape points to match OpenCV's contour format
    contour = points.reshape((-1, 1, 2)).astype(np.int32)

    return contour


def interpolate_labelled_mask(mask):
    # Interpolate only using previously annotated slices
    res = np.zeros_like(mask)

    # Get unique labels in the mask
    labels = np.unique(mask)
    labels = labels[labels != 0]

    # Get z indices of annotated slices for each label
    z_indices_all = {
        label: np.where(np.any(mask == label, axis=(1, 2)))[0]
        for label in labels
    }
    total_steps = sum([len(z) - 1 for z in z_indices_all.values()])

    # Loop through each label
    step = 0
    for label in labels:
        # Obtain the interpolated mask for the current label
        binary_mask = mask == label

        # Get z indices of annotated slices for the current label
        z_indices = z_indices_all[label]
        dist1 = distance_transform_edt(
            binary_mask[z_indices[0]]
        ) - distance_transform_edt(1 - binary_mask[z_indices[0]])
        for i in range(len(z_indices) - 1):
            dist2 = distance_transform_edt(
                binary_mask[z_indices[i + 1]]
            ) - distance_transform_edt(1 - binary_mask[z_indices[i + 1]])
            for z in range(z_indices[i] + 1, z_indices[i + 1]):
                t = (z - z_indices[i]) / (z_indices[i + 1] - z_indices[i])
                binary_mask[z] = distance_transform_interpolation(
                    dist1, dist2, t
                )
            dist1 = dist2
            step += 1
            yield int(100 * step / total_steps)

        # Add the interpolated mask to the result and handle overlapping labels
        res[binary_mask > 0] = label
    return res


def interpolate_binary_mask(mask):
    """
    Interpolates missing slices from a 3D binary mask using distance transforms for smooth transitions.
    """
    # Get z indices of annotated slices
    z_indices = np.where(np.any(mask, axis=(1, 2)))[0]
    dist1 = distance_transform_edt(
        mask[z_indices[0]]
    ) - distance_transform_edt(1 - mask[z_indices[0]])
    for i in range(len(z_indices) - 1):
        dist2 = distance_transform_edt(
            mask[z_indices[i + 1]]
        ) - distance_transform_edt(1 - mask[z_indices[i + 1]])
        for z in range(z_indices[i] + 1, z_indices[i + 1]):
            t = (z - z_indices[i]) / (z_indices[i + 1] - z_indices[i])
            mask[z] = distance_transform_interpolation(dist1, dist2, t)
        dist1 = dist2
    return mask


def distance_transform_interpolation(dist1, dist2, t):
    if not (0 <= t <= 1):
        raise ValueError('Parameter t must be between 0 and 1.')

    if dist1.shape != dist2.shape:
        raise ValueError('Masks must have the same shape.')

    # Interpolate between the distance transforms
    interpolated_dist = (1 - t) * dist1 + t * dist2

    return (interpolated_dist >= 0).astype(np.uint8)
