from qtpy.QtWidgets import (QGridLayout, 
                            QLabel, 
                            QSpinBox, 
                            QGroupBox, 
                            QVBoxLayout, 
                            QMessageBox)

from napari_sbem_viewer._views import SelectDir


DEFAULT_FINE_THICKNESS = 50


class AcquisitionSettings(QGroupBox):
    def __init__(self):
        super().__init__("Acquisition settings")
        self.setLayout(QVBoxLayout())
        
        self.layout().addWidget(QLabel("Overview directory"))
        self.select_overview_dir = SelectDir(self)
        self.layout().addWidget(self.select_overview_dir)
        
        cutting_depth_layout = QGridLayout()
        self.coarse_thickness_label = QLabel("")
        cutting_depth_layout.addWidget(QLabel("Coarse thickness (nm):"), 0, 0)
        cutting_depth_layout.addWidget(self.coarse_thickness_label, 0, 1)
        self.fine_thickness_spinbox = QSpinBox(maximum=999, value=DEFAULT_FINE_THICKNESS)
        cutting_depth_layout.addWidget(QLabel("Fine thickness (nm):"), 1, 0)
        cutting_depth_layout.addWidget(self.fine_thickness_spinbox, 1, 1)
        self.layout().addLayout(cutting_depth_layout)
    
    def show_error(self, title, text):
        QMessageBox.warning(self, title, text)
        