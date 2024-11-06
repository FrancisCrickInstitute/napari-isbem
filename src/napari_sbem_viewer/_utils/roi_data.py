from enum import Enum

import numpy as np

from napari_sbem_viewer._utils.image_utils import get_bounding_boxes_from_mask, convert_data_to_world_coords
from napari_sbem_viewer._utils.registration_utils import transform_image_3d_sitk


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
        coords = self.world_to_roi_coords(coords)
        roi = BoundingBoxROI(coords, len(self.rois)+1)
        self.rois.append(roi)
        
    def add_masks(self, labels_layer):
        labels, offset = transform_image_3d_sitk(labels_layer.data, labels_layer.affine.affine_matrix, labels_layer.scale)
        bboxes = np.asarray(get_bounding_boxes_from_mask((labels > 0).astype(np.uint8)))
        for bbox in bboxes:
            mins = bbox.min(axis=0).astype(int)
            maxes = bbox.max(axis=0).astype(int)
            z1, y1, x1 = mins
            z2, y2, x2 = maxes
            mask = (labels[z1:z2, y1:y2, x1:x2] > 0).astype(np.uint8)
            bbox_position = self.world_to_roi_coords(np.asarray([z1, y1, x1]) + offset)
            roi = MaskROI(bbox_position, mask, len(self.rois)+1)
            self.rois.append(roi)
        
    def set_offset(self, layer, offset):
        self._offset = np.asarray(offset) + layer.data_to_world([0, 0, 0])
        
    def edit(self, idx, coords):
        self.rois[idx].update_coords(self.world_to_roi_coords(coords))
        
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
                
class MaskROI:
    def __init__(self, position, mask, id_):
        self.id = id_
        self.state = ROIState.REMAINING
        self.mask = mask
        self.x1 = position[2]
        self.x2 = position[2] + mask.shape[2]
        self.y1 = position[1]
        self.y2 = position[1] + mask.shape[1]
        self.z1 = position[0]
        self.z2 = position[0] + mask.shape[0]
        self.center = np.array([(self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2, (self.z1 + self.z2) / 2])
        self.size = np.array([self.x2 - self.x1, self.y2 - self.y1, self.z2 - self.z1])
        
    def get_current_slice(self, z_depth):
        z_idx = round(z_depth - self.z1)
        slice = self.mask[z_idx]
        return slice
            
class BoundingBoxROI:
    def __init__(self, coords, id_):
        self.id = id_
        self.update_coords(coords)
        self.state = ROIState.REMAINING
        self.mask = None
        
    def update_coords(self, coords):
        assert self.check_cube(coords)
        mins = coords.min(axis=0)
        maxes = coords.max(axis=0)
        z1, y1, x1 = mins
        z2, y2, x2 = maxes
        self.x1, self.x2 = x1, x2
        self.y1, self.y2 = y1, y2
        self.z1, self.z2 = z1, z2
        self.center = np.array([(x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2])
        self.size = np.array([x2 - x1, y2 - y1, z2 - z1])
        
    def check_cube(self, roi):
        # check if the roi is a cube
        if len(roi) != 8:
            return False
        return True
    