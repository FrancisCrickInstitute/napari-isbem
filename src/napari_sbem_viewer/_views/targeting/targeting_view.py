from qtpy.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from napari_sbem_viewer._views.targeting import (
    AddLabels,
    AddTargetingImage,
    LabelSettings,
)


class TargetingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_targeting_image = AddTargetingImage(parent=self)
        self.add_labels = AddLabels(parent=self)
        self.label_settings = LabelSettings(parent=self)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.add_targeting_image)
        self.layout().addWidget(self.add_labels)
        self.layout().addWidget(self.label_settings)
        self.layout().addStretch(1)

    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)
