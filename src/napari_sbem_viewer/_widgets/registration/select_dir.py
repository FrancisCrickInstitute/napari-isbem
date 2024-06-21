from qtpy.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog



class SelectDir(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())

        self.dir_line = QLineEdit()
        self.dir_line.setReadOnly(True)
        self.layout().addWidget(self.dir_line)

        self.btn = QPushButton("...")
        self.layout().addWidget(self.btn)

        self.btn.clicked.connect(self.select_dir)

    def select_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Directory"
        )
        self.dir_line.setText(dir_path)
        self.dir_line.editingFinished.emit()
        self.dir_line.textChanged.emit(self.dir_line.text())
        self.dir_line.textEdited.emit(self.dir_line.text())
        self.dir_line.returnPressed.emit()
        self.dir_line.selectionChanged.emit()
        self.dir_line.update()