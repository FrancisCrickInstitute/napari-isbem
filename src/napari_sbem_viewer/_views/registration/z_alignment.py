from qtpy.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
)


class ZAlignment(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(title='Z alignment', parent=parent)

        self.setLayout(QGridLayout())

        self.reverse_checkbox = QCheckBox('Reverse Z direction')
        self.layout().addWidget(self.reverse_checkbox, 0, 0, 1, 2)

        self.move_amount_slider = QDoubleSpinBox(
            minimum=0.1, maximum=10, singleStep=0.1, value=1
        )
        self.layout().addWidget(QLabel('Move amount (µm):'), 1, 0)
        self.layout().addWidget(self.move_amount_slider, 1, 1)
        self.move_down_button = QPushButton('Move down')
        self.move_down_button.setAutoRepeat(True)
        self.layout().addWidget(self.move_down_button, 2, 0)
        self.move_up_button = QPushButton('Move up')
        self.move_up_button.setAutoRepeat(True)
        self.layout().addWidget(self.move_up_button, 2, 1)

        self.layout().setRowStretch(self.layout().rowCount(), 1)
