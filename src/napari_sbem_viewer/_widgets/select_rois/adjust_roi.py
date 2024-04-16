from qtpy.QtWidgets import QGroupBox, QGridLayout, QDoubleSpinBox, QLabel


class AdjustROI(QGroupBox):
    def __init__(self, viewer, parent):
        super().__init__("Adjust ROI", parent=parent)
        self.viewer = viewer
        self.viewer.dims.events.current_step.connect(self._on_change_z_depth)
        
        self.setLayout(QGridLayout())
        
        self.layout().addWidget(QLabel("From slice:"), 0, 0)
        self.starting_slice = QDoubleSpinBox(minimum=-9999, maximum=9999, decimals=2, singleStep=0.01)
        self.starting_slice.editingFinished.connect(self._on_adjust_roi_starting_z)
        self.layout().addWidget(self.starting_slice, 0, 1)
        
        self.layout().addWidget(QLabel("To slice:"), 1, 0)
        self.ending_slice = QDoubleSpinBox(minimum=-9999, maximum=9999, decimals=2, singleStep=0.01)
        self.ending_slice.editingFinished.connect(self._on_adjust_roi_ending_z)
        self.layout().addWidget(self.ending_slice, 1, 1)
        
        self.layout().addWidget(QLabel("Current Z depth:"), 2, 0)
        self.current_z_depth = QLabel()
        self.layout().addWidget(self.current_z_depth, 2, 1)
        
    @property
    def bbox_layer(self):
        return self.parentWidget().bbox_layer
        
    def _on_change_z_depth(self, event):
        z_depth = self.viewer.dims.point[0]
        self.current_z_depth.setText(f"{z_depth:.2f}µm")

    def _on_adjust_roi_starting_z(self):
        value = self.starting_slice.value()
        if value > self.ending_slice.value():
            self.starting_slice.setValue(self.ending_slice.value())
            return
        current_idx = self.parentWidget().roi_list.roi_list_widget.currentRow()
        z_data = self.bbox_layer.world_to_data((value, 0, 0))[0]
        self.bbox_layer.data[current_idx][::2, 0] = z_data
        self.bbox_layer.data = self.bbox_layer.data
    
    def _on_adjust_roi_ending_z(self):
        value = self.ending_slice.value()
        if value < self.starting_slice.value():
            self.ending_slice.setValue(self.starting_slice.value())
            return
        current_idx = self.parentWidget().roi_list.roi_list_widget.currentRow()
        z_data = self.bbox_layer.world_to_data((value, 0, 0))[0]
        self.bbox_layer.data[current_idx][1::2, 0] = z_data
        self.bbox_layer.data = self.bbox_layer.data

    def _render_adjust_roi_widget(self, idx):
        if idx == -1:
            self.setVisible(False)
            return
        roi_coords = self.bbox_layer.data[idx]
        starting_slice = int(self.bbox_layer.data_to_world(roi_coords[0])[0])
        ending_slice = int(self.bbox_layer.data_to_world(roi_coords[1])[0])
        self.starting_slice.setValue(starting_slice)
        self.ending_slice.setValue(ending_slice)
        self.setVisible(True)
        