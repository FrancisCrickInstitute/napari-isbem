import numpy as np
from qtpy.QtCore import QObject, Signal
import cv2
from scipy.ndimage import distance_transform_edt
from napari.qt import create_worker
from napari.layers import Layer

from napari_sbem_viewer._utils.registration_utils import convert_affine_to_ndims
from napari_sbem_viewer._reader import get_labels_reader


class DrawROIsModel(QObject):
    interpolation_progress_updated = Signal(int)
    interpolation_started = Signal()
    interpolation_finished = Signal()
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.labels_layer = None
        self.annotated_labels = None
        self.image_layer = None
        self.autofill_labels = False
        
    def add_labels_layer(self, image_layer_name, downsample_factor):
        self.image_layer = self._get_layer(image_layer_name)
        if self.labels_layer is not None:
            raise ValueError("Labels layer already exists")
        labels_shape = [dim // downsample_factor for dim in self.image_layer.data.shape]
        labels = np.zeros(labels_shape, dtype=np.uint8)
        self.labels_layer = self.viewer.add_labels(
            labels,
            name="ROIs",
            scale=[downsample_factor * s for s in self.image_layer.scale],
            )
        self.annotated_labels = np.zeros_like(labels)
        self.labels_layer.events.paint.connect(self._on_labels_data_changed)
        self.image_layer.events.affine.connect(self._on_affine_changed)
        self._on_affine_changed()
        
    def upload_labels(self, file_path, image_layer_name):
        image_layer = self._get_layer(image_layer_name)
        if self.labels_layer is not None:
            raise ValueError("Labels layer already exists")
        reader = get_labels_reader(file_path)
        if reader is None:
            raise ValueError("Unsupported file format")
        labels_layer = Layer.create(*reader(file_path)[0])
        # self._check_dims(image_layer, labels_layer)
        
        self.image_layer = image_layer
        self.annotated_labels = labels_layer.data.copy()
        self.labels_layer = self.viewer.add_layer(labels_layer)
        self.labels_layer.events.paint.connect(self._on_labels_data_changed)
        self.image_layer.events.affine.connect(self._on_affine_changed)
        self._on_affine_changed()
        
    def _on_affine_changed(self):
        self.labels_layer.affine = convert_affine_to_ndims(
            self.image_layer.affine.affine_matrix, self.labels_layer.ndim
            )
        
    def _on_labels_data_changed(self, event):
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
        
    def interpolate_labels(self):
        if self.annotated_labels is None:
            raise ValueError("No labels layer found")
        
        self.interpolation_progress_updated.emit(0)
        self.interpolation_started.emit()
        create_worker(interpolate_labelled_mask, 
                      self.annotated_labels.copy(), 
                      _connect={'returned': self._add_interpolated_labels, 
                                'yielded': self.interpolation_progress_updated.emit,
                                'errored': self._on_finish_interpolation})
        
    def reset_interpolation(self):
        self.interpolation_progress_updated.emit(0)
        self.labels_layer.data = self.annotated_labels
        
    def reset(self):
        self.labels_layer = None
        self.annotated_labels = None
        self.image_layer.events.affine.disconnect(self._on_affine_changed)
        self.image_layer = None
        self.interpolation_progress_updated.emit(0)
        self.interpolation_finished.emit()
        
    def _add_interpolated_labels(self, interpolated_labels):
        self.labels_layer.data = interpolated_labels
        self._on_finish_interpolation()
        
    def _on_finish_interpolation(self):
        self.interpolation_finished.emit()
        
    def _get_layer(self, layer_name):
        try:
            return self.viewer.layers[layer_name]
        except KeyError:
            raise ValueError(f"Layer '{layer_name}' not found.")
        
    def _check_dims(self, image_layer, labels_layer):
        if image_layer.ndim != labels_layer.ndim:
            raise ValueError("Image and labels must have the same number of dimensions.")
        image_extent = image_layer.data_to_world(image_layer.data.shape)
        labels_extent = labels_layer.data_to_world(labels_layer.data.shape)
        if labels_extent != image_extent:
            print(labels_extent, image_extent)
            raise ValueError("Image and labels sizes do not match.")
        
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
    z_indices_all = { label: np.where(np.any(mask == label, axis=(1, 2)))[0] for label in labels }
    total_steps = sum([len(z) - 1 for z in z_indices_all.values()])
    
    # Loop through each label
    step = 0
    for label in labels:     
        # Obtain the interpolated mask for the current label
        binary_mask = mask == label
        
        # Get z indices of annotated slices for the current label
        z_indices = z_indices_all[label]
        dist1 = distance_transform_edt(binary_mask[z_indices[0]]) - distance_transform_edt(1 - binary_mask[z_indices[0]])
        for i in range(len(z_indices) - 1):
            dist2 = distance_transform_edt(binary_mask[z_indices[i+1]]) - distance_transform_edt(1 - binary_mask[z_indices[i+1]])
            for z in range(z_indices[i] + 1, z_indices[i + 1]):
                t = (z - z_indices[i]) / (z_indices[i + 1] - z_indices[i])
                binary_mask[z] = distance_transform_interpolation(dist1, dist2, t)
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
    dist1 = distance_transform_edt(mask[z_indices[0]]) - distance_transform_edt(1 - mask[z_indices[0]])
    for i in range(len(z_indices) - 1):
        dist2 = distance_transform_edt(mask[z_indices[i+1]]) - distance_transform_edt(1 - mask[z_indices[i+1]])
        for z in range(z_indices[i] + 1, z_indices[i + 1]):
            t = (z - z_indices[i]) / (z_indices[i + 1] - z_indices[i])
            mask[z] = distance_transform_interpolation(dist1, dist2, t)
        dist1 = dist2
    return mask


def distance_transform_interpolation(dist1, dist2, t):
    if not (0 <= t <= 1):
        raise ValueError("Parameter t must be between 0 and 1.")
    
    if dist1.shape != dist2.shape:
        raise ValueError("Masks must have the same shape.")

    # Interpolate between the distance transforms
    interpolated_dist = (1 - t) * dist1 + t * dist2

    return (interpolated_dist >= 0).astype(np.uint8)
