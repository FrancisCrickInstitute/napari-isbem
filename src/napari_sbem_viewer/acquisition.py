import os


class Acquisition:
    def __init__(self, live_viewer, tcp_client, roi_layer=None):
        self.tcp_client = tcp_client
        self.live_viewer = live_viewer
        # self.tcp_client.connect()
        self.z_depth = 0
        self.rois = []  # z1, z2, y1, y2, x1, x2
        self.roi_layer = roi_layer
        self.active_rois = set()
        self.inactive_rois = set()
        self.coarse_cutting_depth = None
        self.fine_cutting_depth = None
        
    def start_acquisition(self, coarse_cutting_depth, fine_cutting_depth):
        # check if coarse cutting depth is a multiple of fine cutting depth
        if coarse_cutting_depth % fine_cutting_depth == 0:
            self.coarse_cutting_depth = coarse_cutting_depth
            self.fine_cutting_depth = fine_cutting_depth
        else:
            raise CuttingDepthError("Coarse cutting depth must be a multiple of fine cutting depth.")
        if self.live_viewer.image_dir is None:
            raise FileNotFoundError("Image directory is not set.")
        self.ov_idx = self._get_ov_idx(self.live_viewer.image_dir)
        self.overview_coords = self.get_overview_coords()
        if not self.overview_coords:
            raise FileNotFoundError("Overview dir not recognised.")
        if self.roi_layer is not None:
            self.add_rois(self.roi_layer)
            
        # activate / deactivate ROIs according to z-depth and set the correct cutting depth
        self.active_rois, self.inactive_rois = self.check_rois()
        for roi_idx in self.inactive_rois:
            self.tcp_client.deactivate_roi(roi_idx)
        for roi_idx in self.active_rois:
            self.tcp_client.activate_roi(roi_idx)
        self.set_fine_cutting_depth() if self.active_rois else self.set_coarse_cutting_depth()
            
        if not self.tcp_client.start():
            raise StartAcquisitionError("Failed to start acquisition.")
        print('rois', self.rois)
        self.running = True
        try:
            while self.running:
                # wait for the next overview image
                yield self.live_viewer.wait_for_image()
                
                self.z_depth = self.tcp_client.get_z_depth()
                print(self.z_depth)

                # TODO: only update ROIs on the slice before overviews are acquired

                # check which ROIs are in the subsequent z-depth
                active_rois, inactive_rois = self.check_rois()
                print(active_rois, inactive_rois)
        
                # first deal with case where ROI has been fully imaged
                completed_rois = self.active_rois - active_rois
                for roi_idx in completed_rois:
                    self.tcp_client.deactivate_roi(roi_idx)
                    self.wait_for_user_confirmation(roi_idx, completed=True)
                    self.set_coarse_cutting_depth(self.ov_idx)
                
                # now deal with case where ROI has just been reached
                new_rois = active_rois - self.active_rois
                for roi_idx in new_rois:
                    self.tcp_client.activate_roi(roi_idx)
                    self.wait_for_user_confirmation(roi_idx)
                    self.set_fine_cutting_depth(self.ov_idx)
                
                self.active_rois = active_rois
                self.inactive_rois = inactive_rois

        except:
            # TODO: handle exception where acquisition has to be paused
            raise
    
    def check_rois(self):
        active_rois = set()
        inactive_rois = set()
        for roi_idx, roi in enumerate(self.rois):
            if is_roi_depth_reached(roi, self.z_depth):
                active_rois.add(roi_idx)
            else:
                inactive_rois.add(roi_idx)
        return active_rois, inactive_rois
        
    def get_overview_coords(self):
        return self.tcp_client.get_overview_coords(self.ov_idx)

    def _get_ov_idx(self, ov_dir):
        ov_dirname = os.path.basename(ov_dir)
        ov_idx = int(''.join(filter(str.isdigit, ov_dirname)))
        return ov_idx
            
    def wait_for_confirmation(self, completed=False):
        self.pause_acquisition()
        if completed:
            self.display_completion_dialog()
        else:
            self.display_confirmation_dialog()
        self.start_acquisition()
        
    def add_rois(self, bbox_layer):
        # get the world corods of the lowest z point in the image and subtract from z1 and z2 of the roi
        # to get the z distance from the bottom of the image in 'world units'
        image_layer = self.live_viewer._get_layer()
        
        for idx, roi in enumerate(bbox_layer.data):
            assert check_cube_roi(roi)
            mins = roi.min(axis=0)
            maxes = roi.max(axis=0)
            z1, y1, x1 = mins
            z2, y2, x2 = maxes
            self.rois.append((x1, x2, y1, y2, z1, z2))
            x1_sbem, y1_sbem = x1 + self.overview_coords[0], y1 + self.overview_coords[1]
            w, h = x2 - x1, y2 - y1
            self.tcp_client.add_grid(x1_sbem, y1_sbem, w, h, idx)
        
    def display_confirmation_dialog(self):
        pass
            
    def pause_acquisition(self):
        # TODO: wait for confirmation that sbemimage has paused before continueing
        self.tcp_client.send('PAUSE', 2)
        self.running = False
        self.live_viewer.running = False

    def set_coarse_cutting_depth(self):
        self._set_cutting_depth(self.coarse_cutting_depth)
        self.tcp_client.set_overview_interval(1, self.ov_idx)
        
    def set_fine_cutting_depth(self):
        self._set_cutting_depth(self.fine_cutting_depth)
        self.tcp_client.set_overview_interval(self.coarse_cutting_depth // self.fine_cutting_depth, self.ov_idx)

    def _set_cutting_depth(self, cutting_depth):
        self.tcp_client.set_cutting_depth(cutting_depth)
    
    
def is_roi_depth_reached(roi, z_depth):
    # return true if z_depth is in the roi, else return false
    return roi[-2] <= z_depth <= roi[-1]


def check_cube_roi(roi):
    # check if the roi is a cube
    if len(roi) != 8:
        return False
    return True


class StartAcquisitionError(Exception):
    pass

class CuttingDepthError(Exception):
    pass