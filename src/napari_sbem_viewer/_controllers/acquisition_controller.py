from napari.layers import Labels


class AcquisitionController:
    def __init__(self, view, acquisition_model):
        self.view = view
        self.acquisition_model = acquisition_model
        self.view.roi_settings.setEnabled(False)
        self._init_signals()
        self._populate_roi_combo_box()
        self._on_change_pause_before_acquire_roi(self.view.acquisition_settings.pause_before_acquire_roi_checkbox.checkState())
        self._on_change_pause_after_acquire_roi(self.view.acquisition_settings.pause_after_acquire_roi_checkbox.checkState())
        
    def _init_signals(self):
        # Init acquisition model
        self.acquisition_model.acquisition_info_updated.connect(self.view.acquisition_info.update_acquisition_info)
        self.acquisition_model.rois_updated.connect(self.view.roi_settings.update_roi_info)
        self.acquisition_model.set_fine_thickness(self.view.acquisition_settings.fine_thickness_spinbox.value())
        self.acquisition_model.errored.connect(self.view.show_error)
        self.acquisition_model.live_viewer.initialized.connect(self._on_add_overview)
        self.acquisition_model.live_viewer.cleared.connect(self._on_reset_overview)
        self.acquisition_model.live_viewer.errored.connect(self._on_error_overview)

        # Init tcp settings
        self.view.tcp_settings.start_server_button.clicked.connect(self._on_click_start_server)
        self.view.tcp_settings.stop_server_button.clicked.connect(self._on_click_stop_server)
        
        # Init acquisition settings
        self.view.acquisition_settings.select_overview_dir_button.clicked.connect(self._on_change_ov)
        self.view.acquisition_settings.fine_thickness_spinbox.valueChanged.connect(self.acquisition_model.set_fine_thickness)
        self.view.acquisition_settings.pause_before_acquire_roi_checkbox.stateChanged.connect(self._on_change_pause_before_acquire_roi)
        self.view.acquisition_settings.pause_after_acquire_roi_checkbox.stateChanged.connect(self._on_change_pause_after_acquire_roi)
        
        # Init roi settings
        self.view.roi_settings.roi_combo_box.currentIndexChanged.connect(self._on_roi_layer_changed)
        self.view.roi_settings.table_view.clicked.connect(self._on_click_table)
        self.view.roi_settings.destroyed.connect(self._on_close)
        
        # Init acquisition info
        self.view.acquisition_info.reset_view_button.clicked.connect(self._on_reset_view)

        # Init viewer events
        self.acquisition_model.viewer.layers.events.inserted.connect(self._on_add_layer)
        self.acquisition_model.viewer.layers.events.removed.connect(self._on_remove_layer)
        self.acquisition_model.viewer.dims.events.current_step.connect(self._on_change_z_depth)
        
    def _on_add_overview(self):
        self.view.roi_settings.reset()
        self.view.acquisition_settings.coarse_thickness_label.setText(f"{self.acquisition_model.live_viewer.pixel_size_z*1e3:.0f}")
        self.view.acquisition_settings.overview_dir_line.setText(self.acquisition_model.live_viewer.image_dir)
        self.view.roi_settings.setEnabled(True)
    
    def _on_reset_overview(self):
        self.view.roi_settings.reset()
        self.view.acquisition_settings.coarse_thickness_label.setText("")
        self.view.acquisition_settings.overview_dir_line.setText("")
        self.view.roi_settings.setEnabled(False)
        
    def _on_change_pause_before_acquire_roi(self, check_state):
        is_checked = check_state == 2
        self.acquisition_model.pause_before_acquire_roi = is_checked
        
    def _on_click_table(self, item):
        roi_id = item.row()
        if item.column() == 1:
            region = 'bottom'
        elif item.column() == 2:
            region = 'top'
        else:
            region = 'center'
        self.acquisition_model.focus_on_roi(roi_id, region)
    
    def _on_reset_view(self):
        self.acquisition_model.reset_view()
        
    def _on_change_pause_after_acquire_roi(self, check_state):
        is_checked = check_state == 2
        self.acquisition_model.pause_after_acquire_roi = is_checked
    
    def _on_close(self):
        self.acquisition_model.live_viewer.watching = False

    def _on_change_z_depth(self):
        if not self.acquisition_model.live_viewer.image_dir:
            return
        viewer_z_depth = self.acquisition_model.get_viewer_z_depth()
        self.view.acquisition_info.viewer_z_depth.setText(f"{viewer_z_depth:.2f}µm")
        
    def _on_add_layer(self, event):
        if not isinstance(event.value, Labels):
            return
        self.view.roi_settings.roi_combo_box.addItem(event.value.name)
        
    def _on_remove_layer(self, event):
        if isinstance(event.value, Labels):
            idx = self.view.roi_settings.roi_combo_box.findText(event.value.name)
            if idx >= 0:
                self.view.roi_settings.roi_combo_box.removeItem(idx)
        if event.value == self.acquisition_model.live_viewer.layer:
            self.acquisition_model.live_viewer.reset()
            
    def _populate_roi_combo_box(self):
        self.view.roi_settings.roi_combo_box.addItem("")
        for layer in self.acquisition_model.viewer.layers:
            if isinstance(layer, Labels):
                self.view.roi_settings.roi_combo_box.addItem(layer.name)
        
    def _on_click_start_server(self):
        self.acquisition_model.tcp_server.host = self.view.tcp_settings.host_line_edit.text()
        self.acquisition_model.tcp_server.port = self.view.tcp_settings.port_spinbox.value()
        self.acquisition_model.tcp_server.start()
        self.view.tcp_settings.start_server_button.setEnabled(False)
        self.view.tcp_settings.stop_server_button.setEnabled(True)
        self.view.tcp_settings.host_line_edit.setEnabled(False)
        self.view.tcp_settings.port_spinbox.setEnabled(False)
        
    def _on_click_stop_server(self):
        self.acquisition_model.tcp_server.close()
        self.acquisition_model.tcp_server.wait()
        self.view.tcp_settings.stop_server_button.setEnabled(False)
        self.view.tcp_settings.start_server_button.setEnabled(True)
        self.view.tcp_settings.host_line_edit.setEnabled(True)
        self.view.tcp_settings.port_spinbox.setEnabled(True)
        
    def _on_change_ov(self):
        ov_dir = self.view.acquisition_settings.open_overview_dir_dialog()
        if not ov_dir:
            return
        try:
            self.acquisition_model.live_viewer.start_watching(ov_dir)
        except Exception as e:
            self._on_error_overview(e)
            return     
        
    def _on_roi_layer_changed(self):
        roi_layer = self._get_roi_layer()
        self.acquisition_model.set_roi_layer(roi_layer)
        
    def _on_error_overview(self, error):
        self.view.show_error("Error adding images", str(error))
        
    def _get_roi_layer_names(self):
        return [x.name for x in self.acquisition_model.viewer.layers if isinstance(x, Labels)]
    
    def _get_roi_layer(self):
        self.view.roi_settings.roi_combo_box.currentText()
        try:
            return self.acquisition_model.viewer.layers[self.view.roi_settings.roi_combo_box.currentText()]
        except KeyError:
            return None
        