from napari_sbem_viewer._models.affine_model import AffineTransformChoices


class RegistrationController:
    def __init__(self, view, registration_model):
        self.view = view
        self.registration_model = registration_model
        self.align_planes_model = self.registration_model.align_planes_model
        self.affine_model = self.registration_model.affine_model
        self.affine_model.do_transform = self._on_affine_transform
        self._reset_align_planes_ui()
        self._reset_affine_transform_ui()
        self._on_remove_moving_image()
        self._init_signals()
    
    def _init_signals(self):
        self.view.save_load_transforms.upload_transform_button.clicked.connect(self._on_click_upload_transform)
        self.view.save_load_transforms.save_transform_button.clicked.connect(self._on_click_save_transform)
        self.view.save_load_transforms.reset_transform_button.clicked.connect(self._on_click_reset_transform)
        
        self.view.align_planes.show_button.clicked.connect(self._on_click_show)
        self.view.align_planes.zy_degrees_slider.valueChanged.connect(self._on_update_angle)
        self.view.align_planes.zx_degrees_slider.valueChanged.connect(self._on_update_angle)
        self.view.align_planes.position_slider.valueChanged.connect(self._on_update_position)
        self.view.align_planes.apply_rotation_button.clicked.connect(self._on_click_rotate)
        self.align_planes_model.rotation_started.connect(self._deactivate_transform_buttons)
        self.align_planes_model.rotation_finished.connect(self._on_finish_rotate)
        self.align_planes_model.rotation_errored.connect(self._on_error_rotate)
        self.align_planes_model.activated.connect(lambda: self.view.align_planes.setEnabled(True))
        self.align_planes_model.deactivated.connect(lambda: self.view.align_planes.setEnabled(False))
        
        self.view.z_alignment.reverse_checkbox.stateChanged.connect(self.affine_model._flip_z)
        self.view.z_alignment.move_down_button.clicked.connect(self._on_click_move_down)
        self.view.z_alignment.move_up_button.clicked.connect(self._on_click_move_up)
        
        self.view.affine_2d.start_button.clicked.connect(self._on_click_start)
        self.view.affine_2d.stop_button.clicked.connect(self._on_click_stop)
        self.view.affine_2d.remove_outliers_checkbox.stateChanged.connect(self.affine_model.do_transform)
        self.affine_model.activated.connect(lambda: self.view.affine_2d.setEnabled(True))
        self.affine_model.deactivated.connect(lambda: self.view.affine_2d.setEnabled(False))
        self.affine_model.transform_loaded.connect(self._update_reverse_checkbox)
        
        self.registration_model.moving_layer_added.connect(self._on_add_moving_image)
        self.registration_model.moving_layer_removed.connect(self._on_remove_moving_image)
        
    def _deactivate_transform_buttons(self):
        self.view.align_planes.apply_rotation_button.setEnabled(False)
        self.view.save_load_transforms.upload_transform_button.setEnabled(False)
        self.view.save_load_transforms.save_transform_button.setEnabled(False)
        self.view.save_load_transforms.reset_transform_button.setEnabled(False)
        
    def _activate_transform_buttons(self):
        self.view.align_planes.apply_rotation_button.setEnabled(True)
        self.view.save_load_transforms.upload_transform_button.setEnabled(True)
        self.view.save_load_transforms.save_transform_button.setEnabled(True)
        self.view.save_load_transforms.reset_transform_button.setEnabled(True)
        
    def _on_add_moving_image(self):
        self.view.save_load_transforms.upload_transform_button.setEnabled(True)
        self.view.save_load_transforms.save_transform_button.setEnabled(True)
        self.view.save_load_transforms.reset_transform_button.setEnabled(True)
        self.view.align_planes.setEnabled(True)
        self.view.z_alignment.setEnabled(True)
        self._update_reverse_checkbox()
        
    def _on_remove_moving_image(self):
        self.view.affine_2d.setEnabled(False)
        self.view.save_load_transforms.upload_transform_button.setEnabled(False)
        self.view.save_load_transforms.save_transform_button.setEnabled(False)
        self.view.save_load_transforms.reset_transform_button.setEnabled(False)
        self.view.align_planes.setEnabled(False)
        self.view.z_alignment.setEnabled(False)
        self.view.z_alignment.reverse_checkbox.blockSignals(True)
        self.view.z_alignment.reverse_checkbox.setChecked(False)
        self.view.z_alignment.reverse_checkbox.blockSignals(True)
            
    def _on_click_upload_transform(self):
        file_path = self.view.align_planes.open_transform_file_dialog()
        if not file_path:
            return
        try:
            self.registration_model.load_transform(file_path)
        except Exception as e:
            self.view.show_error("Error", f"Failed to load transform: {e}")
        
    def _on_click_save_transform(self):
        file_path = self.view.align_planes.save_transform_file_dialog()
        if not file_path:
            return
        try:
            self.registration_model.save_transform(file_path)
        except Exception as e:
            self.view.show_error("Error", f"Failed to save transform: {e}")
            
    def _on_click_reset_transform(self):
        if self.view.save_load_transforms.reset_confirmation_dialog():
            self.registration_model.reset_transforms()
            self._reset_align_planes_ui()
            self._reset_affine_transform_ui()
            
    def _on_click_show(self):
        try:
            self.align_planes_model.show_align_planes_window()
            self._on_update_position()
            self._on_update_angle()
        except Exception as e:
            self.view.show_error("Error", f"Failed to display window: {e}")
            
    def _on_update_angle(self):
        self.align_planes_model.update_plane_angle(
            self.view.align_planes.zy_degrees_slider.value(), 
            self.view.align_planes.zx_degrees_slider.value())
        if self.align_planes_model.t is not None:
            self.view.align_planes.position_slider.setValue(self.align_planes_model.t)
    
    def _on_update_position(self):
        self.align_planes_model.update_plane_position(self.view.align_planes.position_slider.value())
        
    def _on_click_rotate(self):
        try:
            zy_degrees = self.view.align_planes.zy_degrees_slider.value()
            zx_degrees = self.view.align_planes.zx_degrees_slider.value()
            self.align_planes_model.apply_rotation(-zy_degrees, -zx_degrees)
        except Exception as e:
            self._on_error_rotate(e)
    
    def _on_finish_rotate(self, affine_matrix):
        self._activate_transform_buttons()
        if affine_matrix is not None:
            self.view.show_info("Success", "Image rotated successfully")
    
    def _on_error_rotate(self, e):
        self._activate_transform_buttons()
        self.view.show_error("Error", f"Failed to rotate image: {e}")
      
    def _on_click_move_down(self):
        offset_amount = self.view.z_alignment.move_amount_slider.value()
        self.affine_model._offset_z(offset_amount)
    
    def _on_click_move_up(self):
        offset_amount = self.view.z_alignment.move_amount_slider.value()
        self.affine_model._offset_z(-offset_amount)
        
    def _on_click_reset(self):
        if self.view.affine_2d.reset_confirmation_dialog():
            self.affine_model.reset_transform()
            self._update_reverse_checkbox()
            
    def _on_click_start(self):
        try:
            self.affine_model.start_registration()
            self._start_affine_transform_ui()
        except Exception as e:
            self.view.show_error("Error", f"Failed to start registration: {e}")
            self._reset_affine_transform_ui()
    
    def _on_affine_transform(self):
        self.affine_model._do_transform(
            flip_z=self.view.z_alignment.reverse_checkbox.isChecked(),
            transform_method=AffineTransformChoices.Affine.value,
            # transform_method=AffineTransformChoices[self.view.affine_2d.model_combobox.currentText()].value,
            remove_outliers=self.view.affine_2d.remove_outliers_checkbox.isChecked()
        )
        
    def _update_reverse_checkbox(self):
        self.view.z_alignment.reverse_checkbox.blockSignals(True)
        if self.affine_model.is_moving_image_flipped():
            self.view.z_alignment.reverse_checkbox.setChecked(True)
        else:
            self.view.z_alignment.reverse_checkbox.setChecked(False)
        self.view.z_alignment.reverse_checkbox.blockSignals(False)
            
    def _on_click_stop(self):
        self._reset_affine_transform_ui()
        self.affine_model.stop_registration()
            
    def _start_affine_transform_ui(self):
        self.view.affine_2d.start_button.setEnabled(False)
        self.view.affine_2d.stop_button.setEnabled(True)  
    
    def _reset_affine_transform_ui(self):
        self.view.affine_2d.start_button.setEnabled(True)
        self.view.affine_2d.stop_button.setEnabled(False)
        
    def _reset_align_planes_ui(self):
        self.view.align_planes.zy_degrees_slider.setValue(0)
        self.view.align_planes.zx_degrees_slider.setValue(0)
        self.view.align_planes.position_slider.setValue(0.5)
        