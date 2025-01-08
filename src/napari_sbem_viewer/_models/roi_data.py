from enum import Enum

import numpy as np

from napari_sbem_viewer._utils.image_utils import get_bounds_from_labels
from napari_sbem_viewer._utils.registration_utils import transform_image_3d_sitk, find_bounds, add_scale_to_transform_matrix


class ROIState(Enum):
    ACQUIRING = 1
    ACQUIRED = 2
    REMAINING = 3

class ROIData:
    def __init__(self):
        self.rois = []
        self.acquiring_rois = set()
        self.remaining_rois = set()
        self._offset = np.asarray([0, 0, 0])
    
    def add_bounding_box(self, coords):
        coords_roi = self.world_to_roi_coords(coords)
        mins = coords_roi.min(axis=0)
        maxes = coords_roi.max(axis=0)
        roi = BoundingBoxROI(mins, maxes - mins, len(self.rois)+1)
        self.rois.append(roi)
        
    def add_masks(self, labels_layer, combine_masks=False):
        labels = labels_layer.data
        if combine_masks:
            labels[labels > 0] = 1
        bounds = get_bounds_from_labels(labels.astype(np.uint8))
        for mins, maxes in bounds:
            # Obtain the mask for the current bounding box
            mask = labels[mins[0]:maxes[0], mins[1]:maxes[1], mins[2]:maxes[2]]
            # Transform the mask and bounds using the transform matrix and scale
            T = add_scale_to_transform_matrix(labels_layer.affine.affine_matrix, labels_layer.scale)
            mins_t, maxes_t = find_bounds(maxes - mins, T, mins)
            mask_t, _ = transform_image_3d_sitk(mask, T)
            mask_t[mask_t > 0] = 1
            position = self.world_to_roi_coords(mins_t)
            size = maxes_t - mins_t
            roi = MaskROI(position, size, mask_t, len(self.rois)+1)
            self.rois.append(roi)
        
    def set_offset(self, layer, offset):
        self._offset = np.asarray(offset) + layer.data_to_world([0, 0, 0])
        
    def edit(self, idx, coords):
        coords_roi = self.world_to_roi_coords(coords)
        mins = coords_roi.min(axis=0)
        maxes = coords_roi.max(axis=0)
        self.rois[idx].update_coords(mins, maxes - mins)
        
    def remove(self, idx):
        del self.rois[idx]
    
    def clear(self):
        self.rois = []
        self.acquiring_rois = set()
        self.acquired_rois = set()
        self._offset = np.asarray([0, 0, 0])
    
    def update_z_depth(self, z_depth):
        self.z_depth = z_depth
        self.remaining_rois = set()
        for roi in self.rois:
            if roi.z1 <= self.z_depth <= roi.z2:
                roi.state = ROIState.ACQUIRING
            elif self.z_depth > roi.z2:
                roi.state = ROIState.ACQUIRED
            else:
                roi.state = ROIState.REMAINING
                
    def world_to_roi_coords(self, coords):
        return coords + self._offset
    
    def roi_to_world_coords(self, coords):
        return coords - self._offset
                
class MaskROI:
    def __init__(self, position, size, mask, id_):
        self.id = id_
        self.state = ROIState.REMAINING
        self.mask = mask
        self.x1 = position[2]
        self.x2 = position[2] + size[2]
        self.y1 = position[1]
        self.y2 = position[1] + size[1]
        self.z1 = position[0]
        self.z2 = position[0] + size[0]
        self.center = np.array([(self.z1 + self.z2) / 2, (self.y1 + self.y2) / 2, (self.x1 + self.x2) / 2])
        self.size = size
        
    def get_current_slice(self, z_depth):
        if not (self.z1 <= z_depth <= self.z2):
            print(f'Warning: z_depth not within mask bounds: {z_depth} not in ({self.z1}, {self.z2})')
            return np.zeros_like(self.mask[0])
        
        mask_z_total = self.z2 - self.z1
        mask_z_cur = z_depth - self.z1
        perc = mask_z_cur / mask_z_total
        
        # Get the slice index between 0 and self.mask.shape[0]
        idx = round(perc * (self.mask.shape[0] - 1))

        return self.mask[idx]
            
class BoundingBoxROI:
    def __init__(self, position, size, id_):
        self.id = id_        
        self.update_coords(position, size)
        self.state = ROIState.REMAINING
        self.mask = None
        
    def update_coords(self, position, size):
        self.x1 = position[2]
        self.x2 = position[2] + size[2]
        self.y1 = position[1]
        self.y2 = position[1] + size[1]
        self.z1 = position[0]
        self.z2 = position[0] + size[0]
        self.center = np.array([(self.z1 + self.z2) / 2, (self.y1 + self.y2) / 2, (self.x1 + self.x2) / 2])
        self.size = size
    