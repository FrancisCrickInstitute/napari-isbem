from qtpy.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from napari_isbem._views.acquisition import (
    AcquisitionInfo,
    AcquisitionSettings,
    ROISettings,
    TCPSettings,
)


class AcquisitionView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.tcp_settings = TCPSettings()
        self.acquisition_settings = AcquisitionSettings()
        self.roi_settings = ROISettings()
        self.acquisition_info = AcquisitionInfo()

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.tcp_settings)
        self.layout().addWidget(self.acquisition_settings)
        self.layout().addWidget(self.roi_settings)
        self.layout().addWidget(self.acquisition_info)
        self.layout().addStretch(1)

    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)
