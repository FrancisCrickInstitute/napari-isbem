import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QLabel, QHeaderView, QPushButton, QSizePolicy


class PrecomputedTransformation(QWidget):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__(parent=parent)
        self.setMinimumWidth(180)
        self.viewer = viewer
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.upload_transformation_button = QPushButton("Upload transformation")
        self.layout().addWidget(self.upload_transformation_button)
        
        self.layout().addWidget(QLabel('Transformation matrix'))
        self.table = QTableWidget()
        self.table.setRowCount(3)
        self.table.setColumnCount(3)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout().addWidget(self.table)
        # # Populate the table with editable text boxes
        # for row in range(3):
        #     for col in range(3):
        #         item = QTableWidgetItem()
        #         item.setFlags(item.flags() | Qt.ItemIsEditable)  # Make the item editable
        #         self.table.setItem(row, col, item)
        
        
        self.register_button = QPushButton("Register")
        self.layout().addWidget(self.register_button)