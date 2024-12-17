from qtpy.QtWidgets import (QGridLayout, 
                            QLabel, 
                            QSpinBox, 
                            QGroupBox, 
                            QVBoxLayout, 
                            QMessageBox,
                            QFileDialog,
                            QHBoxLayout,
                            QLineEdit,
                            QPushButton)


DEFAULT_FINE_THICKNESS = 50


class AcquisitionSettings(QGroupBox):
    def __init__(self):
        super().__init__("Acquisition settings")
        self.setLayout(QVBoxLayout())
        
        self.layout().addWidget(QLabel("Overview directory"))
        self.overview_dir_line = QLineEdit()
        self.overview_dir_line.setReadOnly(True)
        self.select_overview_dir_button = QPushButton("...")
        
        ov_dir_lyt = QHBoxLayout()
        ov_dir_lyt.addWidget(self.overview_dir_line)
        ov_dir_lyt.addWidget(self.select_overview_dir_button)
        self.layout().addLayout(ov_dir_lyt)
        
        cutting_depth_layout = QGridLayout()
        self.coarse_thickness_label = QLabel("")
        cutting_depth_layout.addWidget(QLabel("Coarse thickness (nm):"), 0, 0)
        cutting_depth_layout.addWidget(self.coarse_thickness_label, 0, 1)
        self.fine_thickness_spinbox = QSpinBox(maximum=999, value=DEFAULT_FINE_THICKNESS)
        cutting_depth_layout.addWidget(QLabel("Fine thickness (nm):"), 1, 0)
        cutting_depth_layout.addWidget(self.fine_thickness_spinbox, 1, 1)
        self.layout().addLayout(cutting_depth_layout)
        
    def open_overview_dir_dialog(self):
        return QFileDialog.getExistingDirectory(self, "Select Directory")
    
    def show_error(self, title, text):
        QMessageBox.warning(self, title, text)
        