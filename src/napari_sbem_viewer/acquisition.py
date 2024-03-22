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
        
    def start_acquisition(self):
        if self.live_viewer.image_dir is None:
            raise FileNotFoundError("Image directory is not set.")
        self.overview_coords = self.get_overview_coords(os.path.join(self.live_viewer.image_dir))
        if not self.overview_coords:
            raise FileNotFoundError("Overview dir not recognised.")
        if self.roi_layer is not None:
            self.add_rois(self.roi_layer)
        if not self.tcp_client.start():
            raise StartAcquisitionError("Failed to start acquisition.")
        print('rois', self.rois)
        self.running = True
        try:
            while self.running:
                # wait for the next overview image
                yield self.live_viewer.wait_for_image()
                
                self.z_depth = self.tcp_client.get_z_depth()

                # check if currently in roi
                active_rois = set()
                for roi_idx, roi in enumerate(self.rois):
                    if is_roi_depth_reached(roi, self.z_depth):
                        active_rois.add(roi_idx)
                        if roi_idx not in self.active_rois:
                            self.tcp_client.activate_roi(roi_idx)
                    elif not is_roi_depth_reached(roi, self.z_depth) and roi_idx in self.active_rois:
                        self.tcp_client.deactivate_roi(roi_idx)
                
                if active_rois != self.active_rois:
                    self.set_cutting_depth()
                    # self.wait_for_user_confirmation()
                    self.active_rois = active_rois
                    self.pause_acquisition()
        except:
            # TODO: handle exception where acquisition has to be paused
            raise
        
    def get_overview_coords(self, ov_dir):
        ov_dirname = os.path.basename(ov_dir)
        ov_idx = int(''.join(filter(str.isdigit, ov_dirname)))
        return self.tcp_client.get_overview_coords(ov_idx)
            
    def wait_for_confirmation(self):
        self.pause_acquisition()
        self.display_confirmation_dialog()
        self.start_acquisition()
        
    def add_rois(self, bbox_layer):
        for roi in bbox_layer.data:
            assert check_cube_roi(roi)
            mins = roi.min(axis=0)
            maxes = roi.max(axis=0)
            z1, y1, x1 = mins
            z2, y2, x2 = maxes
            self.rois.append((x1, x2, y1, y2, z1, z2))
            x1_sbem, y1_sbem = x1 + self.overview_coords[0], y1 + self.overview_coords[1]
            w, h = x2 - x1, y2 - y1
            self.tcp_client.add_grid(x1_sbem, y1_sbem, w, h)
        
    def display_confirmation_dialog(self):
        pass
            
    def pause_acquisition(self):
        # TODO: wait for confirmation that sbemimage has paused before continueing
        self.tcp_client.send('PAUSE', 2)
        self.running = False
        # self.live_viewer.running = False

    def set_cutting_depth(self):
        pass
    
    
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