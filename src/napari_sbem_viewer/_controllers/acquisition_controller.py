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
        self._populate_roi_combo_box()
        self._on_change_pause_after_acquire_roi(self.acquisition_settings.pause_after_acquire_roi_checkbox.checkState())
        
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
        self.acquisition_settings.select_overview_dir_button.clicked.connect(self._on_change_ov)
        self.acquisition_settings.fine_thickness_spinbox.valueChanged.connect(self.acquisition_model.set_fine_thickness)
        self.acquisition_settings.pause_after_acquire_roi_checkbox.stateChanged.connect(self._on_change_pause_after_acquire_roi)
        
        # Init roi settings
        self.roi_settings.roi_combo_box.currentIndexChanged.connect(self._on_roi_layer_changed)
        self.roi_settings.table_view.clicked.connect(self._on_click_table)
        self.roi_settings.destroyed.connect(self._on_close)

        # Init viewer events
        self.acquisition_model.viewer.layers.events.inserted.connect(self._on_add_layer)
        self.acquisition_model.viewer.layers.events.removed.connect(self._on_remove_layer)
        self.acquisition_model.viewer.dims.events.current_step.connect(self._on_change_z_depth)
        
    def _on_click_table(self, item):
        roi_id = item.row()
        if item.column() == 1:
            region = 'bottom'
        elif item.column() == 2:
            region = 'top'
        else:
            region = 'center'
        self.acquisition_model.focus_on_roi(roi_id, region)
        
    def _on_change_pause_after_acquire_roi(self, check_state):
        is_checked = check_state == 2
        self.acquisition_model.pause_after_acquire_roi = is_checked
    
    def _on_close(self):
        self.acquisition_model.live_viewer.watching = False

    def _on_change_z_depth(self):
        if not self.acquisition_model.live_viewer.image_dir:
            return
        viewer_z_depth = self.acquisition_model.get_viewer_z_depth()
        self.acquisition_info.viewer_z_depth.setText(f"{viewer_z_depth:.2f}µm")
        
    def _on_add_layer(self, event):
        if not isinstance(event.value, Labels):
            return
        self.roi_settings.roi_combo_box.addItem(event.value.name)
        
    def _on_remove_layer(self, event):
        if isinstance(event.value, Labels):
            idx = self.roi_settings.roi_combo_box.findText(event.value.name)
            if idx >= 0:
                self.roi_settings.roi_combo_box.removeItem(idx)
        if event.value == self.acquisition_model.live_viewer.layer:
            self._on_reset_overview()
            
    def _populate_roi_combo_box(self):
        self.roi_settings.roi_combo_box.addItem("")
        for layer in self.acquisition_model.viewer.layers:
            if isinstance(layer, Labels):
                self.roi_settings.roi_combo_box.addItem(layer.name)
        
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
        
    def _on_change_ov(self):
        ov_dir = self.acquisition_settings.open_overview_dir_dialog()
        if not ov_dir:
            return
        try:
            self._on_reset_overview()
            self.acquisition_model.live_viewer.init_images(ov_dir)
        except ValueError as e:
            self._handle_overview_error(e)
            return
        self.roi_settings.roi_combo_box.setEnabled(True)
        self.acquisition_settings.coarse_thickness_label.setText(f"{self.acquisition_model.live_viewer.pixel_size_z*1e3:.0f}")
        self.acquisition_settings.overview_dir_line.setText(ov_dir)
        create_worker(self.acquisition_model.live_viewer.watch, 
                      _connect={'yielded': self.acquisition_model.live_viewer.append, 'errored': self._handle_overview_error})
            
    def _on_reset_overview(self):
        self.acquisition_model.live_viewer.reset()
        self.acquisition_settings.coarse_thickness_label.setText("")
        self.acquisition_settings.overview_dir_line.setText("")
        self.roi_settings.reset()
        
    def _on_roi_layer_changed(self):
        roi_layer = self._get_roi_layer()
        self.acquisition_model.set_roi_layer(roi_layer)
        
    def _handle_overview_error(self, error):
        self._on_reset_overview()
        self.acquisition_settings.show_error("Error adding images", str(error))
        
    def _get_roi_layer_names(self):
        return [x.name for x in self.acquisition_model.viewer.layers if isinstance(x, Labels)]
    
    def _get_roi_layer(self):
        self.roi_settings.roi_combo_box.currentText()
        try:
            return self.acquisition_model.viewer.layers[self.roi_settings.roi_combo_box.currentText()]
        except KeyError:
            return None
        