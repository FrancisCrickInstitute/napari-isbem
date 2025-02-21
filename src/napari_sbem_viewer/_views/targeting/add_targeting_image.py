from qtpy.QtWidgets import (QGroupBox, 
                            QVBoxLayout, 
                            QPushButton, 
                            QFileDialog)

class AddTargetingImage(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTitle("Import targeting image")
        self.import_targeting_image_button = QPushButton("Import targeting OME-Zarr")
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.import_targeting_image_button)
        
    def open_file_dialog(self):
        return QFileDialog.getExistingDirectory(self, "Select targeting OME-Zarr directory")
    