from qtpy.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog


class SelectDir(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

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
        if dir_path:
            self.dir_line.setText(dir_path)
            self.dir_line.update()
        

class SelectFile(QWidget):
    def __init__(self, parent=None, file_filter="All files (*.*)"):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.file_filter=file_filter

        self.dir_line = QLineEdit()
        self.dir_line.setReadOnly(True)
        self.layout().addWidget(self.dir_line)

        self.btn = QPushButton("...")
        self.layout().addWidget(self.btn)

        self.btn.clicked.connect(self.select_file)

    def select_file(self):
        file_path = QFileDialog.getOpenFileName(self, "Select File", filter=self.file_filter)[0]
        self.dir_line.setText(file_path)
        self.dir_line.update()
        