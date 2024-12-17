from qtpy.QtWidgets import QGroupBox, QGridLayout, QLabel


class AcquisitionInfo(QGroupBox):
    def __init__(self):
        super().__init__("Acquisition info")
        self.setLayout(QGridLayout())
        self.layout().addWidget(QLabel('Viewer Z-depth:'), 0, 0)
        self.viewer_z_depth = QLabel('')
        self.layout().addWidget(self.viewer_z_depth, 0, 1)
        self.layout().addWidget(QLabel('SBEMimage Z-depth:'), 1, 0)
        self.sbemimage_z_depth = QLabel('')
        self.layout().addWidget(self.sbemimage_z_depth, 1, 1)
        self.layout().addWidget(QLabel('Current slice thickness:'), 2, 0)
        self.slice_thickenss = QLabel('')
        self.layout().addWidget(self.slice_thickenss, 2, 1)
        self.layout().addWidget(QLabel('Pause status:'), 3, 0)
        self.pause_status = QLabel('')
        self.layout().addWidget(self.pause_status, 3, 1)
        
    def reset(self):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['ROI ID', 'z1 (µm)', 'z2 (µm)'])
        self.sbemimage_z_depth.setText('')
        self.viewer_z_depth.setText('')
        self.slice_thickenss.setText('')
        self.pause_status.setText('')
    
    def update_acquisition_info(self, z_depth, slice_thickness, pause_status):
        self.sbemimage_z_depth.setText(f'{z_depth:.2f}µm')
        self.slice_thickenss.setText(f'{slice_thickness:.2f}nm')
        self.pause_status.setText('Paused' if pause_status else 'Running')
        