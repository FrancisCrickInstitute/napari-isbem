from qtpy.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QGroupBox, QGridLayout, QLabel


class AcquisitionInfo(QGroupBox):
    def __init__(self):
        super().__init__("Acquisition info")
        self.setLayout(QGridLayout())
        self.layout().addWidget(QLabel('ROIs remaining:'), 1, 0)
        self.remaining_rois = QLabel('')
        self.layout().addWidget(self.remaining_rois, 1, 1)
        self.layout().addWidget(QLabel('Current Z-depth:'), 2, 0)
        self.z_depth = QLabel('')
        self.layout().addWidget(self.z_depth, 2, 1)
        self.layout().addWidget(QLabel('Current slice thickness:'), 3, 0)
        self.slice_thickenss = QLabel('')
        self.layout().addWidget(self.slice_thickenss, 3, 1)
        self.layout().addWidget(QLabel('Pause status:'), 4, 0)
        self.pause_status = QLabel('')
        self.layout().addWidget(self.pause_status, 4, 1)
        self.layout().addWidget(QLabel('Depth until next ROI:'), 5, 0)
        self.depth_until_roi_reached = QLabel('')
        self.layout().addWidget(self.depth_until_roi_reached, 5, 1)
        self.layout().addWidget(QLabel('Depth until ROI acquired:'), 6, 0)
        self.depth_until_roi_acquired = QLabel('')
        self.layout().addWidget(self.depth_until_roi_acquired, 6, 1)
    
    def update(self, remaining_rois, z_depth, slice_thickness, pause_status, depth_until_roi_reached, depth_until_roi_acquired):
        self.remaining_rois.setText(str(remaining_rois))
        self.z_depth.setText(f'{z_depth:.2f}µm')
        self.slice_thickenss.setText(f'{slice_thickness:.2f}nm')
        self.pause_status.setText('Paused' if pause_status else 'Running')
        if depth_until_roi_reached is None:
            self.depth_until_roi_reached.setText('N/A')
        else:
            self.depth_until_roi_reached.setText(f'{depth_until_roi_reached:.2f}µm')
        if depth_until_roi_acquired is None:
            self.depth_until_roi_acquired.setText('N/A')
        else:
            self.depth_until_roi_acquired.setText(f'{depth_until_roi_acquired:.2f}µm')
