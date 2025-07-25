from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
)
from superqt import QLabeledDoubleSlider


class AlignPlanes(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(title='3D rotation', parent=parent)
        self.setMinimumWidth(180)
        self.setLayout(QGridLayout())

        self.show_button = QPushButton('Show rotation')
        self.layout().addWidget(self.show_button, 0, 0, 1, 2)

        form_layout = QFormLayout()
        self.zy_degrees_slider = QLabeledDoubleSlider(Qt.Horizontal)
        self.zy_degrees_slider.setRange(-90, 90)
        self.zy_degrees_slider.setDecimals(1)
        form_layout.addRow(QLabel('Rotate Z-Y'), self.zy_degrees_slider)
        self.zx_degrees_slider = QLabeledDoubleSlider(Qt.Horizontal)
        self.zx_degrees_slider.setRange(-90, 90)
        self.zx_degrees_slider.setDecimals(1)
        form_layout.addRow(QLabel('Rotate Z-X'), self.zx_degrees_slider)
        self.position_slider = QLabeledDoubleSlider(Qt.Horizontal, decimals=3)
        self.position_slider.setRange(0, 1)
        self.position_slider.setSingleStep(0.001)
        form_layout.addRow(QLabel('Position'), self.position_slider)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.layout().addLayout(form_layout, 1, 0, 1, 2)

        self.apply_rotation_button = QPushButton('Apply rotation')
        self.layout().addWidget(self.apply_rotation_button, 2, 0, 1, 2)

    def open_transform_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Open File',
            '',
            'Text Files (*.txt);;All Files (*)',
        )
        return file_path

    def save_transform_file_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Save File', '', 'Text Files (*.txt);;All Files (*)'
        )
        return file_path
