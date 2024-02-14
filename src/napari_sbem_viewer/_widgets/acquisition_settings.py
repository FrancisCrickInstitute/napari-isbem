import napari
from qtpy.QtWidgets import QPushButton, QGridLayout, QLabel, QSpinBox, QGroupBox

from napari_sbem_viewer.util import LiveViewer, convert_to_micrometers


class AcquisitionSettings(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 live_viewer: LiveViewer,
                 ):
        super().__init__("Acquisition settings")
        self.viewer = viewer
        self.live_viewer = live_viewer
        self.setLayout(QGridLayout())
        self.default_coarse_thickness = 250
        self.default_fine_thickness = 50
        self.thickness_unit = 'nm'
        self.live_viewer.pixel_size_z = convert_to_micrometers(self.default_coarse_thickness, self.thickness_unit)
        
        self.layout().addWidget(QLabel("Cutting thickness coarse (nm)"), 0, 0)
        self.coarse_thickness_spinbox = QSpinBox(maximum=999, value=100)
        self.coarse_thickness_spinbox.valueChanged.connect(self._on_change_setting)
        self.layout().addWidget(self.coarse_thickness_spinbox, 0, 1)
        
        self.layout().addWidget(QLabel("Cutting thickness fine (nm)"), 1, 0)
        self.fine_thickness_spinbox = QSpinBox(maximum=999, value=50)
        self.fine_thickness_spinbox.valueChanged.connect(self._on_change_setting)
        self.layout().addWidget(self.fine_thickness_spinbox, 1, 1)
        
        self.save_acquisition_settings_button = QPushButton("Save settings", enabled=False)
        self.save_acquisition_settings_button.clicked.connect(self._on_click_save_acquisition_settings)
        self.layout().addWidget(self.save_acquisition_settings_button, 2, 0, 1, 2)

    def _on_change_setting(self):
        self.save_acquisition_settings_button.setEnabled(True)
        
    def _on_click_save_acquisition_settings(self):
        self.coarse_thickness = self.coarse_thickness_spinbox.value()
        self.fine_thickness = self.fine_thickness_spinbox.value()
        self.live_viewer.pixel_size_z = convert_to_micrometers(self.coarse_thickness, self.thickness_unit)
        self.save_acquisition_settings_button.setEnabled(False)
        