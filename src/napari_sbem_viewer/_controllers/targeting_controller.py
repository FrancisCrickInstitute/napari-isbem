from napari.layers import Image


class TargetingController:
    def __init__(self, view, targeting_model):
        self.view = view
        self.model = targeting_model
        self._populate_image_layer_combo_box()
        self._connect_signals()
        self._update_ui()
        self._update_autofill_checkbox()
        
    def _connect_signals(self):
        # UI events
        self.view.add_targeting_image.import_targeting_image_button.clicked.connect(self._on_click_import_targeting_image)
        self.view.add_labels.add_labels_button.clicked.connect(self._on_click_add_labels)
        self.view.add_labels.upload_labels_button.clicked.connect(self._on_click_upload_labels)
        self.view.label_settings.autofill_checkbox.stateChanged.connect(self._update_autofill_checkbox)
        self.view.label_settings.export_labels_button.clicked.connect(self._on_click_export_labels)
        self.view.label_settings.connected_components_button.clicked.connect(self.model.connected_components)
        self.view.label_settings.merge_nearby_labels_button.clicked.connect(self._on_click_merge_nearby_labels)
        self.view.label_settings.reset_labels_button.clicked.connect(self.model.reset_interpolation)
        self.view.label_settings.interpolate_button.clicked.connect(self._on_click_interpolate)
        
        # Model events
        self.model.interpolation_progress_updated.connect(self.view.label_settings.progress_bar.setValue)
        self.model.interpolation_started.connect(lambda: self.view.label_settings.interpolate_button.setEnabled(False))
        self.model.interpolation_finished.connect(lambda: self.view.label_settings.interpolate_button.setEnabled(True))
        self.model.autofill_labels = self.view.label_settings.autofill_checkbox.isChecked()
        self.model.editing_updated.connect(self._update_ui)
        self.model.layer_model.targeting_layer_added.connect(self._update_ui)
        self.model.layer_model.targeting_layer_removed.connect(self._update_ui)
        self.model.layer_model.labels_layer_added.connect(self._update_ui)
        self.model.layer_model.labels_layer_removed.connect(self._update_ui)
        
    def _update_ui(self):
        if self.model.layer_model.targeting_layer is None:
            self.view.add_targeting_image.setEnabled(True)
            self.view.add_labels.setEnabled(False)
            self.view.label_settings.setEnabled(False)
        elif self.model.layer_model.labels_layer is None:
            self.view.add_targeting_image.setEnabled(False)
            self.view.add_labels.setEnabled(True)
            self.view.label_settings.setEnabled(False)
        else:
            self.view.add_targeting_image.setEnabled(False)
            self.view.add_labels.setEnabled(False)
            self.view.label_settings.setEnabled(self.model.editing_enabled)
            
    def _on_click_import_targeting_image(self):
        file_path = self.view.add_targeting_image.open_file_dialog()
        if not file_path:
            return
        try:
            self.model.layer_model.import_targeting_image(file_path)
        except Exception as e:
            self.view.show_error("Error", f"Failed to load image: {e}")
        
    def _on_click_add_labels(self):
        try:
            downsample_factor = self.view.add_labels.downsample_combo_box.currentText()
            if downsample_factor == "None":
                downsample_factor = 1
            else:
                downsample_factor = int(downsample_factor)
            self.model.add_new_labels_layer(downsample_factor)
        except Exception as e:
            self.view.show_error("Error", f"Failed to add labels layer: {e}")
            
    def _on_click_upload_labels(self):
        try:
            file_path = self.view.add_labels.open_file_dialog()
            if not file_path:
                return
            self.model.upload_existing_labels(file_path)
        except Exception as e:
            self.view.show_error("Error", f"Failed to upload labels: {e}")
            
    def _on_click_export_labels(self):
        try:
            file_path = self.view.label_settings.save_file_dialog()
            if not file_path:
                return
            self.model.layer_model.export_labels_layer(file_path)
        except Exception as e:
            self.view.show_error("Error", f"Failed to export labels: {e}")
            
    def _on_click_merge_nearby_labels(self):
        self.model.merge_nearby_labels(self.view.label_settings.merge_tolerance_spinbox.value())
                
    def _update_autofill_checkbox(self):
        self.model.autofill_labels = self.view.label_settings.autofill_checkbox.isChecked()
        
    def _populate_image_layer_combo_box(self):
        for layer in self.model.viewer.layers:
            if isinstance(layer, Image):
                self.view.add_labels.image_layer_combo_box.addItem(layer.name)
                
    def _on_click_interpolate(self):
        try:
            self.model.interpolate_labels()
        except Exception as e:
            self.view.show_error("Error", f"Failed to interpolate labels: {e}")
            