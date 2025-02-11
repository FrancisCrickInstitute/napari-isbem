from napari.layers import Image, Labels


class DrawROIsController:
    def __init__(self, draw_rois_model, add_labels, label_settings):
        self.model = draw_rois_model
        self.add_labels = add_labels
        self.label_settings = label_settings
        self._populate_image_layer_combo_box()
        self._connect_signals()
        self._update_ui()
        self._update_autofill_checkbox()
        
    def _connect_signals(self):
        self.add_labels.add_labels_button.clicked.connect(self._on_click_add_labels)
        self.add_labels.upload_labels_button.clicked.connect(self._on_click_upload_labels)
        self.label_settings.autofill_checkbox.stateChanged.connect(self._update_autofill_checkbox)
        self.label_settings.export_labels_button.clicked.connect(self._on_click_export_labels)
        self.label_settings.split_connected_components_button.clicked.connect(self.model.split_connected_components)
        self.label_settings.merge_connected_components_button.clicked.connect(self._merge_connected_components)
        self.label_settings.reset_labels_button.clicked.connect(self.model.reset_interpolation)
        self.label_settings.interpolate_button.clicked.connect(self._on_click_interpolate)
        self.model.viewer.layers.events.removed.connect(self._on_remove_layer)
        self.model.interpolation_progress_updated.connect(self.label_settings.progress_bar.setValue)
        self.model.interpolation_started.connect(lambda: self.label_settings.interpolate_button.setEnabled(False))
        self.model.interpolation_finished.connect(lambda: self.label_settings.interpolate_button.setEnabled(True))
        self.model.autofill_labels = self.label_settings.autofill_checkbox.isChecked()
        self.model.labels_added.connect(self._update_ui)
        self.model.labels_removed.connect(self._update_ui)
        self.model.reference_layer_added.connect(self._update_ui)
        self.model.reference_layer_removed.connect(self._update_ui)
        
    def _update_ui(self):
        if self.model.labels_layer is not None:
            self.label_settings.setEnabled(True)
            self.add_labels.setEnabled(False)
        else:
            self.label_settings.setEnabled(False)
            self.add_labels.setEnabled(self.model.reference_layer is not None)
        
    def _merge_connected_components(self):
        self.model.merge_connected_components(self.label_settings.merge_tolerance_spinbox.value())
        
    def _on_click_add_labels(self):
        try:
            downsample_factor = self.add_labels.downsample_combo_box.currentText()
            if downsample_factor == "None":
                downsample_factor = 1
            else:
                downsample_factor = int(downsample_factor)
            self.model.add_labels_layer(downsample_factor)
        except Exception as e:
            self.add_labels.show_error("Error", f"Failed to add labels layer: {e}")
            
    def _on_click_upload_labels(self):
        try:
            file_path = self.add_labels.open_file_dialog()
            if not file_path:
                return
            self.model.upload_labels(file_path)
        except Exception as e:
            self.add_labels.show_error("Error", f"Failed to upload labels: {e}")
            
    def _on_click_export_labels(self):
        try:
            file_path = self.label_settings.save_file_dialog()
            if not file_path:
                return
            self.model.export_labels(file_path)
        except Exception as e:
            self.label_settings.show_error("Error", f"Failed to export labels: {e}")
            
    def _on_remove_layer(self, event):
        if isinstance(event.value, Labels):
            if event.value == self.model.labels_layer:
                self.model.reset()
                
    def _update_autofill_checkbox(self):
        self.model.autofill_labels = self.label_settings.autofill_checkbox.isChecked()
        
    def _populate_image_layer_combo_box(self):
        for layer in self.model.viewer.layers:
            if isinstance(layer, Image):
                self.add_labels.image_layer_combo_box.addItem(layer.name)
                
    def _on_click_interpolate(self):
        try:
            self.model.interpolate_labels()
        except Exception as e:
            self.add_labels.show_error("Error", f"Failed to interpolate labels: {e}")
            