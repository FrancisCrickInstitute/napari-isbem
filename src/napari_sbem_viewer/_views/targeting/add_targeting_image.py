from qtpy.QtWidgets import QFileDialog, QGroupBox, QPushButton, QVBoxLayout


class AddTargetingImage(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTitle('Import targeting image')
        self.import_zarr_button = QPushButton(
            'Import OME-Zarr'
        )
        self.import_tiff_button = QPushButton(
            'Import TIFF'
        )

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.import_zarr_button)
        self.layout().addWidget(self.import_tiff_button)

    def open_zarr_file_dialog(self):
        return QFileDialog.getExistingDirectory(
            self, 'Select targeting OME-Zarr directory'
        )

    def open_tiff_file_dialog(self):
        return QFileDialog.getOpenFileName(
            self, 'Select targeting TIFF file', filter='*.tif *.tiff'
        )[0]
        