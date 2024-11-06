import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from napari.layers.base._base_constants import ActionType
from queue import Queue

from napari_sbem_viewer._widgets.sbemimage_integration import TCPSettings, AcquisitionSettings, AcquisitionInfo
from napari_sbem_viewer._utils.live_viewer import LiveViewer
from napari_sbem_viewer._utils.tcp_server import TCPServer
from napari_sbem_viewer._utils.roi_data import ROIData, ROIState
from napari_sbem_viewer._utils.general_utils import Trigger, is_multiple


class SBEMimageIntegration(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.live_viewer = LiveViewer(self.viewer)
        self.trigger = Trigger()
        self.trigger.signal.connect(self.process_request)
        self.response_queue = Queue()
        self.roi_data = ROIData()
        self.roi_layer = None
        self.bbox_callback = None
        self.is_cutting_thin = False
        self.tcp_server = TCPServer('localhost', 8888, self.trigger, self.response_queue)
        self.acquisition_info = AcquisitionInfo()
            
        self.setLayout(QVBoxLayout())
        self.tcp_settings = TCPSettings(self.viewer, self.tcp_server)
        self.layout().addWidget(self.tcp_settings)
        
        self.acquisition_settings = AcquisitionSettings(self.viewer, self.live_viewer)
        self.acquisition_settings.roi_combo_box.currentIndexChanged.connect(self._on_change_roi_layer)
        self._update_roi_selections()
        self.viewer.layers.events.removed.connect(self._update_roi_selections)
        self.viewer.layers.events.inserted.connect(self._update_roi_selections)
        self.layout().addWidget(self.acquisition_settings)
        
        self.layout().addWidget(self.acquisition_info)
        
        self.layout().addStretch(1)
        
    def process_request(self):
        request = self.trigger.queue.get()
        # validate_request(request)

        slice_thickness = request['slice_thickness']
        
        # update overview spinbox
        ov_dirs = request['overviews']['ov_dirs']
        self.acquisition_settings._update_overview_dirs(ov_dirs)
        ov_idx = None
        for i in range(len(ov_dirs)):
            if ov_dirs[i] == self.acquisition_settings.overview_combo_box.currentText():
                ov_idx = i
        if ov_idx is None:
            # no overview is selected - pause acquisition
            self.tcp_server.pause_acquisition()
            self.tcp_server.send_response()
            return
        
        # check if the z-depth calculated in napari is within a tolerance of the z-depth displayed in sbemimage
        z_depth = request['z_depth']
        self.roi_data.update_z_depth(z_depth)
        
        # check cutting thicknesses are multiples of each other
        try:
            self.get_overview_interval()
        except AssertionError as e:
            QMessageBox.warning(self, "Cutting thickness error", str(e))
            self.tcp_server.pause_acquisition()
            self.tcp_server.send_response()
            return

        # update ROI data
        self.tcp_server.delete_all_grids()
        for roi in self.roi_data.rois:
            x, y = roi.center[:2]
            w, h = roi.size[:2]
            if roi.mask is not None:
                self.tcp_server.add_grid(roi.id, int(x), int(y), int(w), int(h), roi.get_current_slice(z_depth).tolist())
            else:
                self.tcp_server.add_grid(roi.id, x, y, w, h)
            if roi.state == ROIState.ACQUIRING:
                self.tcp_server.activate_grid(roi.id)
                # if new roi is reached
                if roi.id not in self.roi_data.acquiring_rois:
                    self.roi_data.acquiring_rois.add(roi.id)
                    self.tcp_server.pause_acquisition()
            else:
                self.tcp_server.deactivate_grid(roi.id)
                # if the roi has been fully imaged
                if roi.id in self.roi_data.acquiring_rois:
                    self.roi_data.acquiring_rois.remove(roi.id)
                    self.tcp_server.pause_acquisition()
                    
        # update cutting depths
        if self.roi_data.acquiring_rois:
            self.is_cutting_thin = True

        if self.roi_data.acquiring_rois:
            self.tcp_server.set_slice_thickness(self.acquisition_settings.fine_thickness_spinbox.value())
            
        # only set the cutting depth back to coarse thickness if the current depth is a multiple of coarse thickness
        elif is_multiple(z_depth - self.live_viewer.position_z, self.live_viewer.pixel_size_z):
            self.tcp_server.set_slice_thickness(self.live_viewer.pixel_size_z)
            self.is_cutting_thin = False
            
        # if the z-depth is a multiple of the coarse thickness, enable the overview, else disable it
        if is_multiple(z_depth - self.live_viewer.position_z, self.live_viewer.pixel_size_z):
            self.tcp_server.activate_overview(ov_idx)
        else:
            self.tcp_server.deactivate_overview(ov_idx)
        
        # update acquisition info
        is_paused = request['paused']
        self.acquisition_info.update_acquisition_info(z_depth, slice_thickness, is_paused)
        self.acquisition_info.update_roi_info(self.roi_data)
            
        self.tcp_server.send_response()
    
    def get_overview_interval(self):
        coarse_thickness = self.live_viewer.pixel_size_z*1e3
        fine_thickness = self.acquisition_settings.fine_thickness_spinbox.value()
        assert coarse_thickness % fine_thickness == 0, "Coarse thickness must be a multiple of fine thickness."
        return coarse_thickness // fine_thickness
        
    def _on_change_roi_layer(self):
        self.roi_data.clear()
        
        # remove the previous bbox layer callback
        if self.roi_layer and self.bbox_callback:
            self.roi_layer.events.data.disconnect(self.bbox_callback)
        
        # get the new roi layer
        self.roi_layer = self.acquisition_settings.get_roi_layer()
        if self.roi_layer is None:
            self.acquisition_info.update_roi_info(self.roi_data)
            return
        self.roi_data.set_offset(
            self.live_viewer.image_layer,
            [self.live_viewer.position_z, self.live_viewer.position_y, self.live_viewer.position_x]
            )
        
        # if the roi layer exists, update the roi data
        if isinstance(self.roi_layer, napari.layers.Labels):
            self.roi_data.add_masks(self.roi_layer)
        else:
            self.bbox_callback = self.roi_layer.events.data.connect(self._update_rois)
            for roi in self.roi_layer.data:
                self.roi_data.add_bounding_box(roi)
        self.acquisition_info.update_roi_info(self.roi_data)
            
    def _update_rois(self, event):
        if not hasattr(event, 'action'):
            return
        if event.action == ActionType.ADDED:
            for idx in event.data_indices:
                self.roi_data.add_bounding_box(self.roi_layer.data[idx])
        elif event.action == ActionType.REMOVED:
            for idx in event.data_indices:
                self.roi_data.remove(idx)
        elif event.action == ActionType.CHANGED:
            for idx in event.data_indices:
                self.roi_data.edit(idx, self.roi_layer.data[idx])
        self.acquisition_info.update_roi_info(self.roi_data)
                
    def _update_roi_selections(self):
        layer_names = self.acquisition_settings._get_roi_layer_names()
        roi_layer = self.acquisition_settings.roi_combo_box.currentText()
        self.acquisition_settings.roi_combo_box.clear()
        self.acquisition_settings.roi_combo_box.addItem("")
        self.acquisition_settings.roi_combo_box.addItems(layer_names)
    
        # if the selected layer has been deleted, unselect from the combo boxes
        if self.acquisition_settings.roi_combo_box.currentText() not in layer_names:
            self.acquisition_settings.roi_combo_box.setCurrentIndex(0)
            self.roi_data.clear()
        else:
            self.acquisition_settings.roi_combo_box.setCurrentText(roi_layer)
    