import napari
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QMessageBox


class SaveLoadTransforms(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Save / load transforms", parent=parent)
        self.setLayout(QVBoxLayout())
        
        self.upload_transform_button = QPushButton("Upload transform")
        self.save_transform_button = QPushButton("Save transform")
        self.reset_transform_button = QPushButton("Reset transform")
        
        lyt = QHBoxLayout()
        lyt.addWidget(self.upload_transform_button)
        lyt.addWidget(self.save_transform_button)
        self.layout().addLayout(lyt)
        self.layout().addWidget(self.reset_transform_button)
    
    def reset_confirmation_dialog(self):
        reply = QMessageBox.question(self, 'Confirmation',
                                     'Are you sure you want to reset the transformation?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes
    