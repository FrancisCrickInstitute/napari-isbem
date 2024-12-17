from napari.qt import create_worker
from napari.layers import Labels


class AcquisitionController:
    def __init__(self, acquisition_model, tcp_settings, acquisition_settings, roi_settings, acquisition_info):
        self.tcp_settings = tcp_settings
        self.acquisition_model = acquisition_model
        self.acquisition_settings = acquisition_settings
        self.roi_settings = roi_settings
        self.acquisition_info = acquisition_info
        self._init_signals()
        
    def _init_signals(self):
        # Init acquisition model
        self.acquisition_model.acquisition_info_updated.connect(self.acquisition_info.update_acquisition_info)
        self.acquisition_model.rois_updated.connect(self.roi_settings.update_roi_info)
        self.acquisition_model.set_fine_thickness(self.acquisition_settings.fine_thickness_spinbox.value())
        self.acquisition_model.errored.connect(self.acquisition_settings.show_error)

        # Init tcp settings
        self.tcp_settings.start_server_button.clicked.connect(self._on_click_start_server)
        self.tcp_settings.stop_server_button.clicked.connect(self._on_click_stop_server)
        
        # Init acquisition settings
        self.acquisition_settings.select_overview_dir.dir_line.textChanged.connect(self._on_change_ov)
        self.acquisition_settings.fine_thickness_spinbox.valueChanged.connect(self.acquisition_model.set_fine_thickness)
        
        # Init roi settings
        self.roi_settings.roi_combo_box.currentIndexChanged.connect(self._on_roi_layer_changed)

        # Init viewer events
        self.acquisition_model.viewer.layers.events.removed.connect(self._update_roi_selections)
        self.acquisition_model.viewer.layers.events.inserted.connect(self._update_roi_selections)
        self.acquisition_model.viewer.dims.events.current_step.connect(self._on_change_z_depth)
        self._update_roi_selections()
        
    def _on_change_z_depth(self):
        if not self.acquisition_model.live_viewer.image_dir:
            return
        viewer_z_depth = self.acquisition_model.get_viewer_z_depth()
        self.acquisition_info.viewer_z_depth.setText(f"{viewer_z_depth:.2f}µm")
        
    def _on_click_start_server(self):
        self.acquisition_model.tcp_server.host = self.tcp_settings.host_line_edit.text()
        self.acquisition_model.tcp_server.port = self.tcp_settings.port_spinbox.value()
        self.acquisition_model.tcp_server.start()
        self.tcp_settings.start_server_button.setEnabled(False)
        self.tcp_settings.stop_server_button.setEnabled(True)
        self.tcp_settings.host_line_edit.setEnabled(False)
        self.tcp_settings.port_spinbox.setEnabled(False)
        
    def _on_click_stop_server(self):
        self.acquisition_model.tcp_server.close()
        self.acquisition_model.tcp_server.wait()
        self.tcp_settings.stop_server_button.setEnabled(False)
        self.tcp_settings.start_server_button.setEnabled(True)
        self.tcp_settings.host_line_edit.setEnabled(True)
        self.tcp_settings.port_spinbox.setEnabled(True)
        
    def _on_select_overview_dir(self, ov_dir):
        try:
            self.acquisition_model.live_viewer.init_images(ov_dir)
        except ValueError as e:
            self._handle_overview_error(e)
            return
        self.roi_settings.roi_combo_box.setEnabled(True)
        self.acquisition_settings.coarse_thickness_label.setText(f"{self.acquisition_model.live_viewer.pixel_size_z*1e3:.0f}")
        create_worker(self.acquisition_model.live_viewer.watch, 
                      _connect={'yielded': self.acquisition_model.live_viewer.append, 'errored': self._handle_overview_error})
        
    def _on_change_ov(self):
        self._on_reset_overview()
        ov_dir = self.acquisition_settings.select_overview_dir.dir_line.text()
        if ov_dir:
            self._on_select_overview_dir(ov_dir)
        
    def _on_reset_overview(self):
        self.acquisition_model.live_viewer.reset()
        self.acquisition_settings.coarse_thickness_label.setText("")
        self.roi_settings.reset()
        
    def _on_roi_layer_changed(self):
        roi_layer = self._get_roi_layer()
        self.acquisition_model.set_roi_layer(roi_layer)
                
    def _update_roi_selections(self):
        layer_names = self._get_roi_layer_names()
        roi_layer = self.roi_settings.roi_combo_box.currentText()
        self.roi_settings.roi_combo_box.clear()
        self.roi_settings.roi_combo_box.addItem("")
        self.roi_settings.roi_combo_box.addItems(layer_names)
    
        # if the selected layer has been deleted, unselect from the combo boxes
        if self.roi_settings.roi_combo_box.currentText() not in layer_names:
            self.roi_settings.roi_combo_box.setCurrentIndex(0)
            self.acquisition_model.roi_data.clear()
        else:
            self.roi_settings.roi_combo_box.setCurrentText(roi_layer)
        
    def _handle_overview_error(self, error):
        self.acquisition_settings.show_error("Error adding images", str(error))
        self.acquisition_settings.select_overview_dir.dir_line.setText("")
        
    def _get_roi_layer_names(self):
        return [x.name for x in self.acquisition_model.viewer.layers if isinstance(x, Labels)]
    
    def _get_roi_layer(self):
        self.roi_settings.roi_combo_box.currentText()
        try:
            return self.acquisition_model.viewer.layers[self.roi_settings.roi_combo_box.currentText()]
        except KeyError:
            return None
        