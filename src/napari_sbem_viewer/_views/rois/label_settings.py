from qtpy.QtWidgets import (QGroupBox, 
                            QVBoxLayout, 
                            QPushButton, 
                            QProgressBar, 
                            QMessageBox, 
                            QCheckBox,
                            QFileDialog)


class LabelSettings(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTitle("Label settings")
        self.setLayout(QVBoxLayout())
        self.autofill_checkbox = QCheckBox("Autofill")
        self.autofill_checkbox.setChecked(True)
        self.export_labels_button = QPushButton("Export labels")
        self.connected_components_button = QPushButton("Connected components")
        self.reset_labels_button = QPushButton("Reset labels")
        self.interpolate_button = QPushButton("Interpolate labels")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        self.layout().addWidget(self.autofill_checkbox)
        self.layout().addWidget(self.export_labels_button)
        self.layout().addWidget(self.connected_components_button)
        self.layout().addWidget(self.reset_labels_button)
        self.layout().addWidget(self.interpolate_button)
        self.layout().addWidget(self.progress_bar)
        
    def save_file_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(self, 
                                                   "Save File", 
                                                   "", 
                                                   "TIFF Files (*.tif *.tiff);;All Files (*)")
        return file_path
        
    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)
        