from napari.layers import Image, Labels


class DrawROIsController:
    def __init__(self, draw_rois_model, draw_rois_view):
        self.model = draw_rois_model
        self.view = draw_rois_view
        self._populate_image_layer_combo_box()
        self._connect_signals()
        
    def _connect_signals(self):
        self.view.add_labels_button.clicked.connect(self._on_add_labels)
        self.view.interpolate_button.clicked.connect(self._on_click_interpolate)
        self.model.viewer.layers.events.inserted.connect(self._on_add_layer)
        self.model.viewer.layers.events.removed.connect(self._on_remove_layer)
        
    def _on_add_labels(self):
        try:
            image_layer_name = self.view.image_layer_combo_box.currentText()
            downsample_factor = self.view.downsample_combo_box.currentText()
            if downsample_factor == "None":
                downsample_factor = 1
            else:
                downsample_factor = int(downsample_factor)
            self.model.add_labels_layer(image_layer_name, downsample_factor)
        except Exception as e:
            self.view.show_error("Error", f"Failed to add labels layer: {e}")
            
    def _on_add_layer(self, event):
        if not isinstance(event.value, Image):
            return
        self.view.image_layer_combo_box.addItem(event.value.name)
            
    def _on_remove_layer(self, event):
        if isinstance(event.value, Image):
            idx = self.view.image_layer_combo_box.findText(event.value.name)
            if idx >= 0:
                self.view.image_layer_combo_box.removeItem(idx)
        if isinstance(event.value, Labels):
            if event.value == self.model.labels_layer:
                self.model.reset()
        
    def _populate_image_layer_combo_box(self):
        for layer in self.model.viewer.layers:
            if isinstance(layer, Image):
                self.view.image_layer_combo_box.addItem(layer.name)
                
    def _on_click_interpolate(self):
        try:
            self.model.interpolate_labels()
        except Exception as e:
            self.view.show_error("Error", f"Failed to interpolate labels: {e}")
            