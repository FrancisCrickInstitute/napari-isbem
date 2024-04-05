from qtpy.QtWidgets import QGroupBox, QGridLayout, QSpinBox, QLabel


class AdjustROI(QGroupBox):
    def __init__(self, viewer):
        super().__init__("Adjust ROI")
        self.viewer = viewer
        
        self.setLayout(QGridLayout())
        
        self.layout().addWidget(QLabel("From slice:"), 0, 0)
        self.starting_slice = QSpinBox(minimum=-9999, maximum=9999)
        self.layout().addWidget(self.starting_slice, 0, 1)
        
        self.layout().addWidget(QLabel("To slice:"), 1, 0)
        self.ending_slice = QSpinBox(minimum=-9999, maximum=9999)
        self.layout().addWidget(self.ending_slice, 1, 1)
        