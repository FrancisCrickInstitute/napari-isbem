from enum import Enum

import numpy as np


class ROIState(Enum):
    ACQUIRING = 1
    ACQUIRED = 2
    REMAINING = 3

class ROIData:
    def __init__(self):
        self.rois = []
        self.acquiring_rois = set()
        self.remaining_rois = set()
    
    def add(self, coords):
        roi = ROI(coords, 
                  len(self.rois)+1, 
                  self._offset_x, 
                  self._offset_y, 
                  self._offset_z)
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

class ROI:
    def __init__(self, coords, id_, offset_x=0, offset_y=0, offset_z=0):
        self.id = id_
        self.update_coords(coords, offset_x, offset_y, offset_z)
        self.state = ROIState.REMAINING
        
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
    