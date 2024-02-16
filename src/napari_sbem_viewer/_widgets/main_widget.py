import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QVBoxLayout, QTabWidget, QSizePolicy

from napari_sbem_viewer._widgets import ImageRegistration, SBEMimageIntegration, ROISelection


class MainWidget(QTabWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())

        self.sbem_image_integration = SBEMimageIntegration(napari_viewer)
        self.insertTab(0, self.sbem_image_integration, "Config")
           
        self.image_registration = ImageRegistration(napari_viewer)
        self.insertTab(1, self.image_registration, "Registration")
        
        self.roi_selection = ROISelection(napari_viewer)
        self.insertTab(2, self.roi_selection, "ROIs")
        