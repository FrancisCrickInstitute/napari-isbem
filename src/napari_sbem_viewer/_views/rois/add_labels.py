from qtpy.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox, QFileDialog

class AddLabels(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTitle("Add labels")
        self.image_layer_combo_box = QComboBox()
        self.downsample_combo_box = QComboBox()
        self.downsample_combo_box.addItems(["None", "2", "4", "8", "16"])
        self.add_labels_button = QPushButton("Add labels layer")
        self.upload_labels_button = QPushButton("Import labels")
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel("Image layer"))
        self.layout().addWidget(self.image_layer_combo_box)
        self.layout().addWidget(QLabel("Downsample factor"))
        self.layout().addWidget(self.downsample_combo_box)
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
        