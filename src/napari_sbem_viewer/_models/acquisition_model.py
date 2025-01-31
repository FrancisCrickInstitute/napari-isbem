from qtpy.QtCore import QObject, Signal
from napari.layers import Labels

from napari_sbem_viewer._models import ROIData, ROIState, TCPServer, LiveViewer
from napari_sbem_viewer._utils.general_utils import is_multiple


class AcquisitionModel(QObject):
    errored = Signal(str, str)
    acquisition_info_updated = Signal(float, float, bool)
    rois_updated = Signal(ROIData)
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.tcp_server = TCPServer('localhost', 8888)
        self.roi_data = ROIData()
        self.live_viewer = LiveViewer(self.viewer, 'EM overview')
        self.fine_thickness = None
        self.is_cutting_thin = False
        self.last_z_depth = None
        self.pause_after_acquire_roi = False
        self.reset_rois = True
        self.tcp_server.request_received.connect(self.process_request)
    
    def process_request(self, request):
        try:
            slice_thickness = request['slice_thickness']
            z_depth = request['z_depth']
            is_paused = request['paused']
            
            # emit signals to update the GUI
            self.acquisition_info_updated.emit(z_depth, slice_thickness, is_paused)
            self.last_z_depth = z_depth
            
            if not self.live_viewer.is_initialized():
                raise ValueError('Select overview directory before using TCP')
            
            # check if fine thickness is a multiple of coarse thickness
            self._check_fine_thickness()

            # add response commands
            self._update_rois(z_depth)
            self._update_cutting_depth(z_depth)
            
            # emit signal with updated ROI information
            self.rois_updated.emit(self.roi_data)
            
        except Exception as e:
            self.errored.emit("Acquisition error", str(e))
            self.tcp_server.pause_acquisition()
            
        finally:
            self.tcp_server.send_response()
        
    def set_roi_layer(self, roi_layer):
        self.roi_data.clear()

        if roi_layer is not None:
            self.roi_data.set_offset(
                self.live_viewer.layer,
                [self.live_viewer.position_z, -self.live_viewer.size_y // 2, -self.live_viewer.size_x // 2]
                )
            
            # if the roi layer exists, update the roi data
            if isinstance(roi_layer, Labels):
                self.roi_data.add_masks(roi_layer)
            else:
                for roi in roi_layer.data:
                    self.roi_data.add_bounding_box(roi)
                    
            # update the acquisition state of the rois using previous z-depth
            if self.last_z_depth is not None:
                self.roi_data.update_z_depth(self.last_z_depth)
            
            # don't reset ROIs in SBEMimage after setting the ROI layer
            self.reset_rois = False
        
        else:
            self.reset_rois = True
                     
        self.rois_updated.emit(self.roi_data)
        
    def set_fine_thickness(self, fine_thickness):
        self.fine_thickness = fine_thickness
        
    def get_viewer_z_depth(self):
        return self.viewer.dims.point[0] + self.live_viewer.position_z
        
    def _update_rois(self, z_depth):
        if self.reset_rois:
            self.tcp_server.delete_all_grids()
        self.roi_data.update_z_depth(z_depth)
        for roi in self.roi_data.rois:
            y, x = roi.center[1:]
            h, w = roi.size[1:]
            self.tcp_server.add_grid(roi.id, 
                                     [float(x), float(y)], 
                                     [float(w), float(h)], 
                                     [self.live_viewer.position_x, self.live_viewer.position_y])
            if roi.state == ROIState.ACQUIRING:
                self.tcp_server.activate_grid(roi.id)
                self.tcp_server.update_grid_tiles_with_mask(roi.id, roi.get_current_slice(z_depth).tolist())
                # if new roi is reached
                if roi.id not in self.roi_data.acquiring_rois:
                    self.roi_data.acquiring_rois.add(roi.id)
                    if self.pause_after_acquire_roi:
                        self.tcp_server.pause_acquisition()
            else:
                self.tcp_server.deactivate_grid(roi.id)
                # if the roi has been fully imaged
                if roi.id in self.roi_data.acquiring_rois:
                    self.roi_data.acquiring_rois.remove(roi.id)
                    if self.pause_after_acquire_roi:
                        self.tcp_server.pause_acquisition()
                    
    def _update_cutting_depth(self, z_depth):
        if self.roi_data.acquiring_rois:
            self.is_cutting_thin = True

        if self.roi_data.acquiring_rois:
            self.tcp_server.set_slice_thickness(int(self.fine_thickness))
            
        # only set the cutting depth back to coarse thickness if the current depth is a multiple of coarse thickness
        elif is_multiple(z_depth - self.live_viewer.position_z, self.live_viewer.pixel_size_z):
            self.tcp_server.set_slice_thickness(int(self.live_viewer.pixel_size_z * 1e3))
            self.is_cutting_thin = False
        
    def _check_fine_thickness(self):
        if self.fine_thickness is None:
            raise ValueError("Fine thickness is not set.")
        coarse_thickness = self.live_viewer.pixel_size_z*1e3
        assert coarse_thickness % self.fine_thickness == 0, "Coarse thickness must be a multiple of fine thickness."       
        
    