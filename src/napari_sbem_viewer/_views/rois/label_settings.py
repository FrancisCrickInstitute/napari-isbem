from qtpy.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QProgressBar, QMessageBox, QCheckBox


class LabelSettings(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTitle("Label settings")
        self.setLayout(QVBoxLayout())
        self.autofill_checkbox = QCheckBox("Autofill")
        self.reset_labels_button = QPushButton("Reset labels")
        self.interpolate_button = QPushButton("Interpolate labels")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        self.layout().addWidget(self.autofill_checkbox)
        self.layout().addWidget(self.reset_labels_button)
        self.layout().addWidget(self.interpolate_button)
        self.layout().addWidget(self.progress_bar)
        
    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)
        