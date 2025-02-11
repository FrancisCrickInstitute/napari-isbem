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
        
        self.acquisition.acquisition_model.live_viewer.initialized.connect(self.registration.registration_model.add_fixed_image)
        self.acquisition.acquisition_model.live_viewer.cleared.connect(self.registration.registration_model.remove_fixed_image)
        self.registration.registration_model.moving_layer_added.connect(self.draw_rois.draw_rois_model.add_reference_layer)
        self.registration.registration_model.moving_layer_removed.connect(self.draw_rois.draw_rois_model.remove_reference_layer)