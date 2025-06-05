from qtpy.QtWidgets import (
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from napari_sbem_viewer._views.registration import (
    Affine2d,
    AlignPlanes,
    SaveLoadTransforms,
    ZAlignment,
)


class RegistrationView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.save_load_transforms = SaveLoadTransforms(parent=self)

        self.align_planes = AlignPlanes(parent=self)
        self.z_alignment = ZAlignment(parent=self)
        self.affine_2d = Affine2d(parent=self)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.save_load_transforms)
        self.layout().addWidget(self.align_planes)
        self.layout().addWidget(self.z_alignment)
        self.layout().addWidget(self.affine_2d)
        self.layout().addStretch(1)

    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)
