import numpy as np
from enum import Enum

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
        roi = ROI(coords, len(self.rois)+1)
        self.rois.append(roi)
        
    def edit(self, idx, coords):
        self.rois[idx].update_coords(coords)
        
    def remove(self, idx):
        del self.rois[idx]
    
    def clear(self):
        self.rois = []
        self.acquiring_rois = set()
        self.acquired_rois = set()
    
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
    def __init__(self, coords, id_):
        self.id = id_
        self.update_coords(coords)
        self.state = ROIState.REMAINING
        
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