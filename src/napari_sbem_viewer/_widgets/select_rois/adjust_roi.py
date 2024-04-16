from qtpy.QtWidgets import QGroupBox, QGridLayout, QDoubleSpinBox, QLabel, QAbstractSpinBox


class AdjustROI(QGroupBox):
    def __init__(self, viewer):
        super().__init__("Adjust ROI")
        self.viewer = viewer
        self.viewer.dims.events.current_step.connect(self._on_change_z_depth)
        
        self.setLayout(QGridLayout())
        
        self.layout().addWidget(QLabel("From slice:"), 0, 0)
        self.starting_slice = QDoubleSpinBox(minimum=-9999, maximum=9999, decimals=2, singleStep=0.01)
        self.layout().addWidget(self.starting_slice, 0, 1)
        
        self.layout().addWidget(QLabel("To slice:"), 1, 0)
        self.ending_slice = QDoubleSpinBox(minimum=-9999, maximum=9999, decimals=2, singleStep=0.01)
        self.layout().addWidget(self.ending_slice, 1, 1)
        
        self.layout().addWidget(QLabel("Current Z depth:"), 2, 0)
        self.current_z_depth = QLabel()
        self.layout().addWidget(self.current_z_depth, 2, 1)
        
    def _on_change_z_depth(self, event):
        z_depth = self.viewer.dims.point[0]
        self.current_z_depth.setText(f"{z_depth:.2f}µm")