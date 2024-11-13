import napari
from qtpy.QtWidgets import QVBoxLayout, QVBoxLayout, QTabWidget

from napari_sbem_viewer._widgets import RegistrationWidget, AcquisitionWidget, SelectROIsWidget


class SBEMViewerWidget(QTabWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())

        self.sbem_image_integration = AcquisitionWidget(napari_viewer)
        self.insertTab(0, self.sbem_image_integration, "Acquisition")
           
        self.image_registration = RegistrationWidget(napari_viewer)
        self.insertTab(1, self.image_registration, "Registration")
        
        self.roi_selection = SelectROIsWidget(napari_viewer)
        self.insertTab(2, self.roi_selection, "ROIs")
        