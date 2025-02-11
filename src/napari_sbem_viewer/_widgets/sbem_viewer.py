import napari
from qtpy.QtWidgets import QVBoxLayout, QVBoxLayout, QTabWidget

from napari_sbem_viewer._widgets import RegistrationWidget, AcquisitionWidget, DrawROIsWidget


class SBEMViewerWidget(QTabWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())

        self.acquisition = AcquisitionWidget(napari_viewer)
        self.insertTab(0, self.acquisition, "Acquisition")

        self.registration = RegistrationWidget(napari_viewer)
        self.insertTab(1, self.registration, "Registration")
        
        self.draw_rois = DrawROIsWidget(napari_viewer)
        self.insertTab(3, self.draw_rois, "Draw ROIs")
        
        self.acquisition.acquisition_model.live_viewer.initialized.connect(self.registration.registration_model.on_load_live_viewer)
        self.acquisition.acquisition_model.live_viewer.cleared.connect(self.registration.registration_model.on_remove_live_viewer)
        