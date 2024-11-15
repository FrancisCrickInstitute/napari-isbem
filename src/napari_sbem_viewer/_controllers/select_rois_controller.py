class SelectROIsController:
    def __init__(self, select_rois_model, add_labels, add_bounding_boxes, roi_list):
        self.model = select_rois_model
        self.add_labels = add_labels
        self.add_bounding_boxes = add_bounding_boxes
        self.roi_list = roi_list
        self._init_signals()
        self._update_labels_selections()
        
    def _init_signals(self):
        self.add_labels.import_labels_button.clicked.connect(self._on_click_import_labels)
        self.add_bounding_boxes.upload_button.clicked.connect(self._on_add_bboxes_from_labels)
        self.model.viewer.layers.events.removed.connect(self._on_remove_bbox_layer)
        self.model.viewer.layers.events.inserted.connect(self._update_labels_selections)
        self.model.viewer.layers.events.removed.connect(self._update_labels_selections)
        self.model.viewer.dims.events.current_step.connect(self._on_change_z_depth)
        self.roi_list.table_view.clicked.connect(self._on_click_roi_table)
        self.roi_list.add_button.clicked.connect(self._on_click_add_roi)
        self.roi_list.remove_button.clicked.connect(self._on_click_remove_roi)
        self.model.bbox_selected.connect(self.roi_list.select_rois)
        self.model.bbox_added.connect(self.roi_list.add_roi_to_table)
        self.model.bbox_removed.connect(self.roi_list.remove_rois_from_table)
        
    def _on_remove_bbox_layer(self, event):
        if event.value == self.model.bbox_layer:
            self.model.bbox_layer = None
            self.roi_list.clear()
            
    def _on_add_bboxes_from_labels(self):
        try:
            layer_name = self.add_bounding_boxes.get_layer_name()
            self.model.add_bboxes_from_labels(layer_name)
        except Exception as e:
            self.add_bounding_boxes.show_error("Error adding labels", str(e))
        
    def _update_labels_selections(self):
        layer_names = self.model.get_labels_layer_names()
        self.add_bounding_boxes.update_labels_layers(layer_names)
    
    def _on_click_import_labels(self):
        file_path = self.add_labels.open_file_dialog()
        if not file_path:
            return     
        try:
            self.model.import_labels(file_path)
        except Exception as e:
            self.add_labels.show_error("Error", str(e))
            
    def _on_change_z_depth(self):
        z_depth = self.model.viewer.dims.point[0]
        self.roi_list.current_z_depth_label.setText(f"Current Z: {z_depth:.2f}µm")
        
    def _on_click_roi_table(self):
        print('clicked')
        indices = self.roi_list.get_selected_rows()
        self.model.select_bboxes(indices)

    def _on_click_add_roi(self):
        self.model.add_bbox_layer()
        
    def _on_click_remove_roi(self):
        indices = self.roi_list.get_selected_rows()
        self.model.remove_bboxes(indices)
        
    def _on_update_bbox_z(self, item):
        self.model.update_bbox_z(item)
        
    def _reset_z_viewer(self, z):
        self.model.reset_z_viewer(z)
