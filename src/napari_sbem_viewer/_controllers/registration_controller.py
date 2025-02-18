from napari_sbem_viewer._models.manual_registration_model import AffineTransformChoices


class RegistrationController:
    def __init__(self, registration_model, align_planes, manual_registration, select_images):
        self.model = registration_model
        self.align_planes_model = self.model.align_planes_model
        self.align_planes = align_planes
        self.select_images = select_images
        self.manual_registration = manual_registration
        self.manual_registration_model = self.model.manual_registration_model
        self.manual_registration_model.do_transform = self._on_affine_transform
        self.select_images = select_images
        self._reset_align_planes_ui()
        self._reset_affine_transform_ui()
        self.align_planes.setEnabled(False)
        self.manual_registration.setEnabled(False)
        self._init_signals()
    
    def _init_signals(self):
        self.select_images.import_targeting_image_button.clicked.connect(self._on_click_import_targeting_image)
        self.select_images.upload_transform_button.clicked.connect(self._on_click_upload_transform)
        self.select_images.save_transform_button.clicked.connect(self._on_click_save_transform)
        
        self.align_planes.show_button.clicked.connect(self._on_click_show)
        self.align_planes.zy_degrees_slider.valueChanged.connect(self._on_update_angle)
        self.align_planes.zx_degrees_slider.valueChanged.connect(self._on_update_angle)
        self.align_planes.position_slider.valueChanged.connect(self._on_update_position)
        self.align_planes.apply_rotation_button.clicked.connect(self._on_click_rotate)
        self.align_planes_model.rotation_started.connect(lambda: self.align_planes.apply_rotation_button.setEnabled(False))
        self.align_planes_model.rotation_finished.connect(self._on_finish_rotate)
        self.align_planes_model.rotation_errored.connect(self._on_error_rotate)
        self.align_planes_model.activated.connect(lambda: self.align_planes.setEnabled(True))
        self.align_planes_model.deactivated.connect(lambda: self.align_planes.setEnabled(False))
        
        self.manual_registration.reset_button.clicked.connect(self._on_click_reset)
        self.manual_registration.reverse_checkbox.stateChanged.connect(self.manual_registration_model._flip_z)
        self.manual_registration.move_down_button.clicked.connect(self._on_click_move_down)
        self.manual_registration.move_up_button.clicked.connect(self._on_click_move_up)
        self.manual_registration.model_combobox.addItems([str(model.name) for model in AffineTransformChoices])
        self.manual_registration.model_combobox.currentIndexChanged.connect(self.manual_registration_model.do_transform)
        self.manual_registration.start_button.clicked.connect(self._on_click_start)
        self.manual_registration.stop_button.clicked.connect(self._on_click_stop)
        self.manual_registration.remove_outliers_checkbox.stateChanged.connect(self.manual_registration_model.do_transform)
        self.manual_registration_model.activated.connect(self._on_activate_manual_registration)
        self.manual_registration_model.deactivated.connect(self._on_deactivate_manual_registration)
        
        self.model.viewer.layers.events.removed.connect(self.model._on_remove_layer)
        
    def _on_click_import_targeting_image(self):
        file_path = self.select_images.open_file_dialog()
        if not file_path:
            return
        try:
            self.model.import_targeting_image(file_path)
        except Exception as e:
            self.select_images.show_error("Error", f"Failed to load image: {e}")
            
    def _on_click_upload_transform(self):
        file_path = self.align_planes.open_transform_file_dialog()
        if not file_path:
            return
        try:
            self.model.load_transform(file_path)
        except Exception as e:
            self.align_planes.show_error("Error", f"Failed to load transform: {e}")
        
    def _on_click_save_transform(self):
        file_path = self.align_planes.save_transform_file_dialog()
        if not file_path:
            return
        try:
            self.model.save_transform(file_path)
        except Exception as e:
            self.align_planes.show_error("Error", f"Failed to save transform: {e}")
            
    def _on_click_show(self):
        try:
            self.align_planes_model.show_align_planes_window()
            self._on_update_position()
            self._on_update_angle()
        except Exception as e:
            self.align_planes.show_error("Error", f"Failed to display window: {e}")
            
    def _on_update_angle(self):
        self.align_planes_model.update_plane_angle(
            self.align_planes.zy_degrees_slider.value(), 
            self.align_planes.zx_degrees_slider.value())
        if self.align_planes_model.t is not None:
            self.align_planes.position_slider.setValue(self.align_planes_model.t)
    
    def _on_update_position(self):
        self.align_planes_model.update_plane_position(self.align_planes.position_slider.value())
        
    def _on_click_rotate(self):
        try:
            zy_degrees = self.align_planes.zy_degrees_slider.value()
            zx_degrees = self.align_planes.zx_degrees_slider.value()
            self.align_planes_model.apply_rotation(-zy_degrees, -zx_degrees)
        except Exception as e:
            self._on_error_rotate(e)
    
    def _on_finish_rotate(self):
        self.align_planes.apply_rotation_button.setEnabled(True)
        self.align_planes.show_info("Success", "Image rotated successfully")
    
    def _on_error_rotate(self, e):
        self.align_planes.apply_rotation_button.setEnabled(True)
        self.align_planes.show_error("Error", f"Failed to rotate image: {e}")
      
    def _on_click_move_down(self):
        offset_amount = self.manual_registration.move_amount_slider.value()
        self.manual_registration_model._offset_z(offset_amount)
    
    def _on_click_move_up(self):
        offset_amount = self.manual_registration.move_amount_slider.value()
        self.manual_registration_model._offset_z(-offset_amount)
        
    def _on_click_reset(self):
        if self.manual_registration.reset_confirmation_dialog():
            self.manual_registration_model.reset_transform()
            self._update_reverse_checkbox()
            
    def _on_click_start(self):
        try:
            self.manual_registration_model.start_registration()
            self._start_affine_transform_ui()
        except Exception as e:
            self.manual_registration.show_error(f"Failed to start registration: {e}")
            self._reset_affine_transform_ui()
    
    def _on_affine_transform(self):
        self.manual_registration_model._do_transform(
            flip_z=self.manual_registration.reverse_checkbox.isChecked(),
            transform_method=AffineTransformChoices.Affine.value,
            # transform_method=AffineTransformChoices[self.manual_registration.model_combobox.currentText()].value,
            remove_outliers=self.manual_registration.remove_outliers_checkbox.isChecked()
        )
        
    def _on_activate_manual_registration(self):
        self.manual_registration.setEnabled(True)
        self._update_reverse_checkbox()
        
    def _on_deactivate_manual_registration(self):
        self.manual_registration.setEnabled(False)
        self.manual_registration.reverse_checkbox.blockSignals(True)
        self.manual_registration.reverse_checkbox.setChecked(False)
        self.manual_registration.reverse_checkbox.blockSignals(True)
        
    def _update_reverse_checkbox(self):
        self.manual_registration.reverse_checkbox.blockSignals(True)
        if self.manual_registration_model.is_moving_image_flipped():
            self.manual_registration.reverse_checkbox.setChecked(True)
        else:
            self.manual_registration.reverse_checkbox.setChecked(False)
        self.manual_registration.reverse_checkbox.blockSignals(False)
            
    def _on_click_stop(self):
        self._reset_affine_transform_ui()
        self.manual_registration_model.stop_registration()
            
    def _start_affine_transform_ui(self):
        self.manual_registration.start_button.setEnabled(False)
        self.manual_registration.stop_button.setEnabled(True)  
    
    def _reset_affine_transform_ui(self):
        self.manual_registration.start_button.setEnabled(True)
        self.manual_registration.stop_button.setEnabled(False)
        
    def _reset_align_planes_ui(self):
        self.align_planes.zy_degrees_slider.setValue(0)
        self.align_planes.zx_degrees_slider.setValue(0)
        self.align_planes.position_slider.setValue(0.5)
        