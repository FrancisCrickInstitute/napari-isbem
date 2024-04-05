import napari
from qtpy.QtWidgets import QVBoxLayout, QVBoxLayout, QTabWidget

from napari_sbem_viewer._widgets.registration import Registration
from napari_sbem_viewer._widgets.sbemimage_integration import SBEMimageIntegration
from napari_sbem_viewer._widgets.select_rois import SelectROIs


class MainWidget(QTabWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())

        self.sbem_image_integration = SBEMimageIntegration(napari_viewer)
        self.insertTab(0, self.sbem_image_integration, "Config")
           
        self.image_registration = Registration(napari_viewer)
        self.insertTab(1, self.image_registration, "Registration")
        
        self.roi_selection = SelectROIs(napari_viewer)
        self.insertTab(2, self.roi_selection, "ROIs")
        