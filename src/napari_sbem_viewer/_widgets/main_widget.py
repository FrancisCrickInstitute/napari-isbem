import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QVBoxLayout, QTabWidget, QSizePolicy

from napari_sbem_viewer._widgets import ImageRegistration, SBEMimageIntegration, ROISelection


class MainWidget(QTabWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        self.sizePolicy().setVerticalPolicy(QSizePolicy.Minimum)

        self.sbem_image_integration = SBEMimageIntegration(napari_viewer)
        self.insertTab(0, self.sbem_image_integration, "Config")
           
        self.image_registration = ImageRegistration(napari_viewer)
        self.insertTab(1, self.image_registration, "Registration")
        
        self.roi_selection = ROISelection(napari_viewer)
        self.insertTab(2, self.roi_selection, "ROIs")
        
        size_policy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        size_policy.setVerticalStretch(0)
        # size_policy.setHorizontalPolicy(QSizePolicy.ShrinkFlag)
        self.setSizePolicy(size_policy)
        self.sbem_image_integration.setSizePolicy(size_policy)
        
    def _set_widget(self, widget_):
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().addWidget(widget_)
        widget.setMinimumHeight(0)
        return widget
        