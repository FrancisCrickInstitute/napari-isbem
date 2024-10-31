from enum import Enum

import cv2
import numpy as np
from skimage import measure

from napari_sbem_viewer._utils.image_utils import downsample_3d_image_sitk, get_bounding_boxes_from_mask
from napari_sbem_viewer._utils.registration_utils import transform_image_3d


class ROIState(Enum):
    ACQUIRING = 1
    ACQUIRED = 2
    REMAINING = 3

class ROIData:
    def __init__(self):
        self.rois = []
        self.acquiring_rois = set()
        self.remaining_rois = set()
    
    def add_bounding_box(self, coords):
        roi = BoundingBoxROI(
            coords, 
            len(self.rois)+1, 
            self._offset_x, 
            self._offset_y, 
            self._offset_z)
        self.rois.append(roi)
        
    def add_masks(self, labels_layer):
        labels = transform_image_3d(labels_layer.data, labels_layer.affine.affine_matrix, labels_layer.scale)
        bboxes = get_bounding_boxes_from_mask((labels > 0).astype(np.uint8))
        for bbox in bboxes:
            z1, z2 = bbox[0][0], bbox[5][0]
            y1, y2 = bbox[0][1], bbox[5][1]
            x1, x2 = bbox[0][2], bbox[5][2]
            mask = (labels[z1:z2, y1:y2, x1:x2] > 0).astype(np.uint8)
            roi = MaskROI(
                mask, 
                len(self.rois)+1, 
                self._offset_x + x1, 
                self._offset_y + y1, 
                self._offset_z + z1)
            self.rois.append(roi)
        
    def set_offsets(self, offset_x, offset_y, offset_z):
        self._offset_x = offset_x
        self._offset_y = offset_y
        self._offset_z = offset_z
        
    def edit(self, idx, coords):
        self.rois[idx].update_coords(coords,
                                     self._offset_x,
                                     self._offset_y,
                                     self._offset_z)
        
    def remove(self, idx):
        del self.rois[idx]
    
    def clear(self):
        self.rois = []
        self.acquiring_rois = set()
        self.acquired_rois = set()
        self._offset_x = 0
        self._offset_y = 0
        self._offset_z = 0
    
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
                
                
class MaskROI:
    def __init__(self, mask, id_, offset_x=0, offset_y=0, offset_z=0):
        self.id = id_
        self.state = ROIState.REMAINING
        self.mask = mask
        self.x1 = offset_x
        self.x2 = offset_x + mask.shape[-1]
        self.y1 = offset_y
        self.y2 = offset_y + mask.shape[-2]
        self.z1 = offset_z
        self.z2 = offset_z + mask.shape[-3]
        self.center = np.array([(self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2, (self.z1 + self.z2) / 2])
        self.size = np.array([self.x2 - self.x1, self.y2 - self.y1, self.z2 - self.z1])
        
    def get_current_slice(self, z_depth):
        z_idx = round(z_depth - self.z1)
        slice = self.mask[z_idx]
        return slice
            
class BoundingBoxROI:
    def __init__(self, coords, id_, offset_x=0, offset_y=0, offset_z=0):
        self.id = id_
        self.update_coords(coords, offset_x, offset_y, offset_z)
        self.state = ROIState.REMAINING
        self.mask = None
        
    def update_coords(self, coords, offset_x=0, offset_y=0, offset_z=0):
        assert self.check_cube(coords)
        mins = coords.min(axis=0)
        maxes = coords.max(axis=0)
        z1, y1, x1 = mins
        z2, y2, x2 = maxes
        x1 += offset_x
        x2 += offset_x
        y1 += offset_y
        y2 += offset_y
        z1 += offset_z
        z2 += offset_z 
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
    