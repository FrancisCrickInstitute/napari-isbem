from qtpy.QtWidgets import (QGroupBox, 
                            QVBoxLayout, 
                            QHBoxLayout, 
                            QLabel, 
                            QComboBox, 
                            QPushButton, 
                            QMessageBox, 
                            QFileDialog)

class AddLabels(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTitle("Add labels")
        self.downsample_combo_box = QComboBox()
        self.downsample_combo_box.addItems(["None", "2", "4", "8", "16"])
        self.add_labels_button = QPushButton("Add labels layer")
        self.upload_labels_button = QPushButton("Import labels")
        
        self.setLayout(QVBoxLayout())
        img_lyt = QHBoxLayout()
        self.layout().addLayout(img_lyt)
        
        downsample_lyt = QHBoxLayout()
        downsample_lyt.addWidget(QLabel("Downsample"))
        downsample_lyt.addWidget(self.downsample_combo_box, 1)
        self.layout().addLayout(downsample_lyt)
        
        self.layout().addWidget(self.add_labels_button)
        self.layout().addWidget(self.upload_labels_button)
        
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 
                                                   "Open File", 
                                                   "", 
                                                   "TIFF Files (*.tif *.tiff);;All Files (*)")
        return file_path
        
    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)
        