import numpy as np
from qtpy.QtCore import QObject
import cv2
from scipy.ndimage import distance_transform_edt


class DrawROIsModel(QObject):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.labels_layer = None
        self.annotated_labels = None
        
    def add_labels_layer(self, image_layer_name, downsample_factor):
        image_layer = self._get_layer(image_layer_name)
        if self.labels_layer is not None:
            raise ValueError("Labels layer already exists")
        labels_shape = [dim // downsample_factor for dim in image_layer.data.shape]
        labels = np.zeros(labels_shape, dtype=np.uint8)
        self.labels_layer = self.viewer.add_labels(
            labels,
            name="ROIs",
            scale=[downsample_factor * s for s in image_layer.scale],
            )
        self.annotated_labels = np.zeros_like(labels)
        self.labels_layer.events.paint.connect(self._on_labels_data_changed)
        
    def _on_labels_data_changed(self, event):
        if event.type != 'paint':
            return
        layer = event.source
        z_coord = event.value[0][0][0][0]
        label = int(event.value[0][2])
        if label > 0:
            x_coords = np.array([coord[2][0] for coord, _, _ in event.value])
            y_coords = np.array([coord[1][0] for coord, _, _ in event.value])
            contours = create_contour(x_coords, y_coords)
            cv2.fillPoly(layer.data[z_coord], [contours], color=label)
            layer.data = layer.data
        self.annotated_labels[z_coord] = layer.data[z_coord]
        
    def interpolate_labels(self):
        # Interpolate only using previously annotated slices
        mask = self.annotated_labels
        res = np.zeros_like(mask)
        
        # Loop through each label
        for label in np.unique(mask):
            if label == 0:
                continue
            # Obtain the interpolated mask for the current label
            interpolated_mask = interpolate_mask_3d(mask == label)
            
            # Add the interpolated mask to the result and handle overlapping labels
            res[interpolated_mask > 0] = label
        self.labels_layer.data = res
        
    def reset(self):
        self.labels_layer = None
        self.annotated_labels = None
        
    def _get_layer(self, layer_name):
        try:
            return self.viewer.layers[layer_name]
        except KeyError:
            raise ValueError(f"Layer '{layer_name}' not found.")
        
        
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


def interpolate_mask_3d(mask):
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
