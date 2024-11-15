from qtpy.QtWidgets import (QVBoxLayout, 
                            QWidget, 
                            QPushButton, 
                            QFileDialog, 
                            QMessageBox)


class AddLabels(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setLayout(QVBoxLayout())
        self.import_labels_button = QPushButton("Import Labels")
        self.layout().addWidget(self.import_labels_button)

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 
                                                   "Save File", 
                                                   "", 
                                                   "Tiff Files (*.tif *.tiff);;All Files (*)")
        return file_path
    
    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)
        