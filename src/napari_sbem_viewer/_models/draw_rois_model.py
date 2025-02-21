import numpy as np
from qtpy.QtCore import QObject, Signal
import cv2
from scipy.ndimage import distance_transform_edt
from napari.qt import create_worker
import tifffile
from napari_ome_zarr import napari_get_reader
from napari.layers import Layer

from napari_sbem_viewer._utils.image_utils import connected_components_sitk, merge_nearby_objects
from napari_sbem_viewer._utils.general_utils import round_up_to_odd


class DrawROIsModel(QObject):
    interpolation_progress_updated = Signal(int)
    interpolation_started = Signal()
    interpolation_finished = Signal()
    labels_added = Signal(object)
    labels_removed = Signal()
    targeting_layer_added = Signal(object)
    targeting_layer_removed = Signal()
    editing_updated = Signal()
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.labels_layer = None
        self.annotated_labels = None
        self.autofill_labels = False
        self.targeting_layer = None
        self.editing_enabled = True
        
    def import_targeting_image(self, file_path):
        if not file_path.endswith('.ome.zarr'):
            raise ValueError("Invalid file format. Must be an OME-Zarr file.")
        reader = napari_get_reader(file_path)
        layer = Layer.create(*reader(file_path)[0])
        layer.contrast_limits = (0, 65535)
        self.targeting_layer = layer
        self.targeting_layer_added.emit(layer)
        self.viewer.add_layer(layer)
    
    def remove_targeting_layer(self):
        self.targeting_layer = None
        self.reset()
        self.targeting_layer_removed.emit()
        
    def add_labels_layer(self, downsample_factor):
        if self.labels_layer is not None:
            raise ValueError("Labels layer already exists")
        labels_shape = [dim // downsample_factor for dim in self.targeting_layer.data.shape]
        labels = np.zeros(labels_shape, dtype=np.uint8)
        self.labels_layer = self.viewer.add_labels(
            labels,
            name="ROIs",
            scale=[downsample_factor * s for s in self.targeting_layer.scale],
            )
        self.annotated_labels = np.zeros_like(labels)
        self.labels_layer.events.paint.connect(self._on_paint_labels)
        self.labels_added.emit(self.labels_layer)
        
    def upload_labels(self, file_path):
        if self.labels_layer is not None:
            raise ValueError("Labels layer already exists")
        
        labels = tifffile.imread(file_path)
        scale_factors = calculate_scale(labels.shape, self.targeting_layer.data.shape)
        scale = [s * f for s, f in zip(self.targeting_layer.scale, scale_factors)]
        self.annotated_labels = labels.copy()
        self.labels_layer = self.viewer.add_labels(
            labels,
            name="ROIs",
            scale=scale,
            )
        self.labels_layer.events.paint.connect(self._on_paint_labels)
        self.labels_added.emit(self.labels_layer)
        
    def export_labels(self, file_path):
        if self.labels_layer is None:
            raise ValueError("No labels layer found")
        tifffile.imsave(file_path, self.labels_layer.data)
        
    def connected_components(self):
        if self.labels_layer is None:
            raise ValueError("No labels layer found")
        cc_mask = connected_components_sitk(self.labels_layer.data)
        self.labels_layer.data = cc_mask
        self.annotated_labels = cc_mask.copy()
        
    def merge_nearby_labels(self, tolerance):
        tolerance_px = round_up_to_odd(tolerance / self.labels_layer.scale[0])
        merged_labels = merge_nearby_objects(self.annotated_labels, tolerance_px)
        self.labels_layer.data = merged_labels
        self.annotated_labels = merged_labels.copy()
        
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
        
    def reset_targeting_layer(self):
        self._remove_layer(self.targeting_layer)
        self.targeting_layer = None
        self.targeting_layer_removed.emit()
        self.reset_labels()
        
    def reset_labels(self):
        self._remove_layer(self.labels_layer)
        self._remove_layer(self.targeting_layer)
        self.labels_layer = None
        self.annotated_labels = None
        self.interpolation_progress_updated.emit(0)
        self.interpolation_finished.emit()
        self.labels_removed.emit()
        self.targeting_layer_removed.emit()

    def enable_editing(self, enabled):
        self.editing_enabled = enabled == True
        self.editing_updated.emit()
        
    def _on_remove_layer(self, event):
        if event.value == self.labels_layer:
            self.reset_labels()
        if event.value == self.targeting_layer:
            self.reset_targeting_layer()
        
    def _remove_layer(self, layer):
        try:
            self.viewer.layers.remove(layer)
        except:
            pass
        
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
        self.labels_layer.data = interpolated_labels
        self._on_finish_interpolation()
        
    def _on_finish_interpolation(self):
        self.interpolation_finished.emit()
        
    def _get_layer(self, layer_name):
        try:
            return self.viewer.layers[layer_name]
        except KeyError:
            raise ValueError(f"Layer '{layer_name}' not found.")
        
        
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
