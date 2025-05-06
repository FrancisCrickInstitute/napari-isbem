from qtpy.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QPushButton,
    QComboBox,
)


class Affine2d(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(title='2D affine', parent=parent)

        self.setLayout(QGridLayout())
        
        self.method_combo_box = QComboBox()
        self.layout().addWidget(self.method_combo_box, 0, 0, 1, 2)
        
        self.remove_outliers_checkbox = QCheckBox('Remove outliers')
        self.layout().addWidget(self.remove_outliers_checkbox, 1, 0, 1, 2)

        self.start_button = QPushButton('Start')
        self.layout().addWidget(self.start_button, 2, 0)

        self.stop_button = QPushButton('Stop')
        self.layout().addWidget(self.stop_button, 2, 1)

        self.layout().setRowStretch(self.layout().rowCount(), 1)
