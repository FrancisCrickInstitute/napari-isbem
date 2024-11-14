class AlignPlanesController:
    def __init__(self, align_planes_model, align_planes, select_images):
        self.model = align_planes_model
        self.align_planes = align_planes
        self.select_images = select_images
        self._init_signals()
        self.align_planes.reset_ui()
        
    def _init_signals(self):
        self.align_planes.upload_transform_button.clicked.connect(self._on_click_upload_transform)
        self.align_planes.save_transform_button.clicked.connect(self._on_click_save_transform)
        self.align_planes.save_ome_zarr_button.clicked.connect(self._on_click_save_ome_zarr)
        self.align_planes.show_button.clicked.connect(self._on_click_show)
        self.align_planes.zy_degrees_slider.valueChanged.connect(self._on_update_angle)
        self.align_planes.zx_degrees_slider.valueChanged.connect(self._on_update_angle)
        self.align_planes.position_slider.valueChanged.connect(self._on_update_position)
        self.select_images.moving_combo_box.currentIndexChanged.connect(self._on_change_moving_image)
        
    def _on_click_save_ome_zarr(self):
        save_path = self.align_planes.save_ome_zarr_file_dialog()
        if not save_path:
            return
        try:
            self.model.save_ome_zarr(save_path)
            self.align_planes.show_info("Success", f"Image saved successfully")
        except Exception as e:
            self.align_planes.show_error(self, "Error", f"Failed to save image: {e}")
            
    def _on_click_upload_transform(self):
        file_path = self.align_planes.open_transform_file_dialog()
        if not file_path:
            return
        try:
            self.model.upload_transform(file_path)
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
            self.model.show_align_planes_window()
            self._on_update_position()
            self._on_change_angle()
        except Exception as e:
            self.align_planes.show_error("Error", f"Failed to display window: {e}")
            
    def _on_update_angle(self):
        position = self.model.update_plane_angle(
            self.align_planes.zy_degrees_slider.value(), 
            self.align_planes.zx_degrees_slider.value())
        self.align_planes.position_slider.setValue(position)
    
    def _on_update_position(self):
        self.model.update_plane_position(self.align_planes.position_slider.value())
        
    def _on_click_register(self):
        try:
            self.model.apply_transform()
            self.show_info("Success", "Image rotated successfully")
        except Exception as e:
            self.show_error("Error", f"Failed to rotate image: {e}")
      
    def _on_change_moving_image(self):
        self.model.reset()
        