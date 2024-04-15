import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from napari.layers.base._base_constants import ActionType
import math
from queue import Queue

from napari_sbem_viewer._widgets.sbemimage_integration import TCPSettings, AcquisitionSettings, AcquisitionInfo
from napari_sbem_viewer.live_viewer import LiveViewer
from napari_sbem_viewer.tcp_server import TCPServer
from napari_sbem_viewer.roi_data import ROIData
from napari_sbem_viewer.utils import Trigger


class SBEMimageIntegration(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.live_viewer = LiveViewer(self.viewer)
        self.trigger = Trigger()
        self.trigger.signal.connect(self.process_request)
        self.response_queue = Queue()
        self.roi_data = ROIData()
        self.bbox_layer = None
        self.tcp_server = TCPServer('localhost', 8888, self.trigger, self.response_queue)
            
        self.setLayout(QVBoxLayout())
        self.tcp_settings = TCPSettings(self.viewer, self.tcp_server)
        self.layout().addWidget(self.tcp_settings)
        
        self.acquisition_settings = AcquisitionSettings(self.viewer, self.live_viewer)
        self.acquisition_settings.roi_combo_box.currentIndexChanged.connect(self._on_change_roi_layer)
        self._update_roi_selections()
        self.viewer.layers.events.removed.connect(self._update_roi_selections)
        self.viewer.layers.events.inserted.connect(self._update_roi_selections)
        self.layout().addWidget(self.acquisition_settings)
        
        self.acquisition_info = AcquisitionInfo()
        self.layout().addWidget(self.acquisition_info)
        
        self.layout().addStretch(1)
        
        
    def process_request(self):
        request = self.trigger.queue.get()
        # validate_request(request)

        slice_thickness = request['slice_thickness']
        self.live_viewer.pixel_size_z = self.acquisition_settings.coarse_thickness_spinbox.value() * 1e-3
        
        # update overview spinbox
        ov_dirs = request['overviews']['ov_dirs']
        ov_coords = request['overviews']['ov_coords']
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
        napari_z_depth = self.live_viewer.get_current_z_depth()        
        if napari_z_depth is not None and not math.isclose(z_depth, napari_z_depth):
            QMessageBox.warning(self, "Z-depth error", f"Missmatch between Napari ({napari_z_depth:.2f}µm) and SBEMimage ({z_depth:.2f}µm) Z-depths.\n Check if the Z-depth in SBEMimage is correct and the correct number of overview images are available.")
            self.tcp_server.pause_acquisition()
            self.tcp_server.send_response()
            return
        
        # check cutting thicknesses are multiples of each other
        try:
            overview_interval = self.get_overview_interval()
        except AssertionError as e:
            QMessageBox.warning(self, "Cutting thickness error", str(e))
            self.tcp_server.pause_acquisition()
            self.tcp_server.send_response()
            return

        # update ROI data
        self.roi_data.update_z_depth(z_depth)
        self.tcp_server.delete_all_grids()
        for roi in self.roi_data.rois:
            x, y = roi.center[:2] + ov_coords[ov_idx]
            w, h = roi.size[:2]
            self.tcp_server.add_grid(roi.id, x, y, w, h)
            if roi.active:
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
            self.tcp_server.set_slice_thickness(self.acquisition_settings.fine_thickness_spinbox.value())
            self.tcp_server.set_overview_interval(ov_idx, overview_interval)
        else:
            self.tcp_server.set_slice_thickness(self.acquisition_settings.coarse_thickness_spinbox.value())
            self.tcp_server.set_overview_interval(ov_idx, 1)
        
        # update acquisition info
        is_paused = request['paused']
        depth_until_roi_reached = min([roi.z1 - float(z_depth) for roi in self.roi_data.rois if roi.z1 > z_depth], default=None)
        depth_until_roi_acquired = min([roi.z2 - z_depth for roi in self.roi_data.rois if roi.z2 > z_depth and roi.id in self.roi_data.acquiring_rois], default=None)
        self.acquisition_info.update(len(self.roi_data.remaining_rois), z_depth, slice_thickness, is_paused, depth_until_roi_reached, depth_until_roi_acquired)
            
        self.tcp_server.send_response()
    
    def get_overview_interval(self):
        coarse_thickness = self.acquisition_settings.coarse_thickness_spinbox.value()
        fine_thickness = self.acquisition_settings.fine_thickness_spinbox.value()
        assert coarse_thickness % fine_thickness == 0, "Coarse thickness must be a multiple of fine thickness."
        return coarse_thickness // fine_thickness
        
    def _on_change_roi_layer(self):
        self.roi_data.clear()
        
        # remove the previous bbox layer callback
        if self.bbox_layer and self.bbox_callback:
            self.bbox_layer.events.data.disconnect(self.bbox_callback)
            
        # get the new roi layer
        self.bbox_layer = self.acquisition_settings.get_bbox_layer()
        if self.bbox_layer is None:
            return
        
        # if the roi layer exists, update the roi data
        self.bbox_callback = self.bbox_layer.events.data.connect(self._update_rois)
        for roi in self.bbox_layer.data:
            self.roi_data.add(roi)
            
    def _update_rois(self, event):
        if not hasattr(event, 'action'):
            return
        if event.action == ActionType.ADDED:
            for idx in event.data_indices:
                self.roi_data.add(self.bbox_layer.data[idx])
        elif event.action == ActionType.REMOVED:
            for idx in event.data_indices:
                self.roi_data.remove(idx)
        elif event.action == ActionType.CHANGED:
            for idx in event.data_indices:
                self.roi_data.edit(idx, self.bbox_layer.data[idx])
                
    def _update_roi_selections(self):
        layer_names = self.acquisition_settings._get_bbox_layer_names()
        bbox_layer = self.acquisition_settings.roi_combo_box.currentText()
        self.acquisition_settings.roi_combo_box.clear()
        self.acquisition_settings.roi_combo_box.addItem("")
        self.acquisition_settings.roi_combo_box.addItems(layer_names)
    
        # if the selected layer has been deleted, unselect from the combo boxes
        if self.acquisition_settings.roi_combo_box.currentText() not in layer_names:
            self.acquisition_settings.roi_combo_box.setCurrentIndex(0)
            self.roi_data.clear()
        else:
            self.acquisition_settings.roi_combo_box.setCurrentText(bbox_layer)
    