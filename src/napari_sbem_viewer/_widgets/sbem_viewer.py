import napari
from qtpy.QtWidgets import QVBoxLayout, QVBoxLayout, QTabWidget

from napari_sbem_viewer._widgets import RegistrationWidget, AcquisitionWidget, TargetingWidget


class SBEMViewerWidget(QTabWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())

        self.acquisition = AcquisitionWidget(napari_viewer)
        self.insertTab(0, self.acquisition, "Acquisition")
        
        self.targeting = TargetingWidget(napari_viewer)
        self.insertTab(1, self.targeting, "Targeting")

        self.registration = RegistrationWidget(napari_viewer)
        self.insertTab(2, self.registration, "Registration")
        
        self.acquisition.acquisition_model.live_viewer.initialized.connect(self.registration.registration_model.add_fixed_image)
        self.acquisition.acquisition_model.live_viewer.cleared.connect(self.registration.registration_model.remove_fixed_image)
        self.targeting.draw_rois_model.targeting_layer_added.connect(self.registration.registration_model.add_moving_image)
        self.targeting.draw_rois_model.targeting_layer_removed.connect(self.registration.registration_model.remove_moving_image)
        # connect add ROI event to add an ROI layer to the registration model
        self.targeting.draw_rois_model.labels_added.connect(self.registration.registration_model.align_planes_model.add_labels_layer)
        self.targeting.draw_rois_model.labels_removed.connect(self.registration.registration_model.align_planes_model.remove_labels_layer)
        self.registration.registration_model.align_planes_model.rotation_finished.connect(lambda m: self.targeting.draw_rois_model.enable_editing(m is None))
        