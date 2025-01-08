from napari_sbem_viewer._models.manual_registration_model import AffineTransformChoices


class ManualRegistrationController:
    def __init__(self, manual_registration_model, manual_registration_view, select_images):
        self.view = manual_registration_view
        self.model = manual_registration_model
        self.model.do_transform = self._on_transform
        self.select_images = select_images
        self._init_signals()
        self._disable_ui()

    def _init_signals(self):
        self.select_images.moving_combo_box.currentIndexChanged.connect(self._on_change_moving_image)
        self.select_images.fixed_combo_box.currentIndexChanged.connect(self._on_change_fixed_image)
        
        self.view.upload_transform_button.clicked.connect(self._on_click_upload_transform)
        self.view.save_button.clicked.connect(self._on_click_save_transform)
        self.view.reset_button.clicked.connect(self._on_click_reset)
        
        self.view.reverse_checkbox.stateChanged.connect(self.model._flip_z)
        self.view.move_down_button.clicked.connect(self._on_click_move_down)
        self.view.move_up_button.clicked.connect(self._on_click_move_up)
        
        self.view.model_combobox.addItems([str(model.name) for model in AffineTransformChoices])
        self.view.model_combobox.currentIndexChanged.connect(self.model.do_transform)
        self.view.start_button.clicked.connect(self._on_click_start)
        self.view.stop_button.clicked.connect(self._on_click_stop)
        self.view.remove_outliers_checkbox.stateChanged.connect(self.model.do_transform)
        
    def _on_click_move_down(self):
        offset_amount = self.view.move_amount_slider.value()
        self.model._offset_z(offset_amount)
    
    def _on_click_move_up(self):
        offset_amount = self.view.move_amount_slider.value()
        self.model._offset_z(-offset_amount)
        
    def _on_click_upload_transform(self):
        file_path = self.view.open_file_dialog()
        if file_path:
            try:
                self.model.upload_transform(file_path)
                self._update_reverse_checkbox()
            except Exception as e:
                self.view.show_error(f"Failed to load file: {e}")
                
    def _on_click_save_transform(self):
        file_path = self.view.save_file_dialog()
        if file_path:
            try:
                self.model.save_transform(file_path)
            except Exception as e:
                self.view.show_error(f"Failed to save file: {e}")
        
    def _on_click_reset(self):
        if self.view.reset_confirmation_dialog():
            self.model.reset_transform()
            self._update_reverse_checkbox()
            
    def _on_click_start(self):
        try:
            self.model.start_registration()
            self._enable_ui()
        except Exception as e:
            self.view.show_error(f"Failed to start registration: {e}")
            self._disable_ui()
    
    def _on_transform(self):
        self.model._do_transform(
            flip_z=self.view.reverse_checkbox.isChecked(),
            transform_method=AffineTransformChoices.Affine.value,
            # transform_method=AffineTransformChoices[self.view.model_combobox.currentText()].value,
            remove_outliers=self.view.remove_outliers_checkbox.isChecked()
        )
        
    def _on_change_moving_image(self):
        self.model.moving_image_layer = self.select_images.get_moving_layer()
        self._update_reverse_checkbox()
        
    def _on_change_fixed_image(self):
        self.model.fixed_image_layer = self.select_images.get_fixed_layer()
        
    def _update_reverse_checkbox(self):
        self.view.reverse_checkbox.blockSignals(True)
        if self.model.is_moving_image_flipped():
            self.view.reverse_checkbox.setChecked(True)
        else:
            self.view.reverse_checkbox.setChecked(False)
        self.view.reverse_checkbox.blockSignals(False)
            
    def _on_click_stop(self):
        self._disable_ui()
        self.model.stop_registration()
            
    def _enable_ui(self):
        self.view.start_button.setEnabled(False)
        self.view.stop_button.setEnabled(True)
        
    def _disable_ui(self):        
        self.view.start_button.setEnabled(True)
        self.view.stop_button.setEnabled(False)
        