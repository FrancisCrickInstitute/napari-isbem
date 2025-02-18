import napari
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QFileDialog, QMessageBox


class ImageSettings(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__("Image settings", parent=parent)
        self.viewer = viewer
        self.setLayout(QVBoxLayout())
        
        self.import_targeting_image_button = QPushButton("Import Targeting Image")
        self.upload_transform_button = QPushButton("Upload Transform")
        self.save_transform_button = QPushButton("Save Transform")
        
        self.layout().addWidget(self.import_targeting_image_button)
        lyt = QHBoxLayout()
        lyt.addWidget(self.upload_transform_button)
        lyt.addWidget(self.save_transform_button)
        self.layout().addLayout(lyt)

    def open_file_dialog(self):
        return QFileDialog.getExistingDirectory(self, "Select targeting OME-Zarr directory")
        
    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)
        