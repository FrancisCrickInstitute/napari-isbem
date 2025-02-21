import napari
from qtpy.QtWidgets import QVBoxLayout, QVBoxLayout, QTabWidget

from napari_sbem_viewer._controllers import RegistrationController, AcquisitionController, TargetingController
from napari_sbem_viewer._models import AcquisitionModel, RegistrationModel, DrawROIsModel, StackViewer
from napari_sbem_viewer._views import AcquisitionView, RegistrationView, TargetingView


class SBEMViewerWidget(QTabWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())

        self.acquisition_model = AcquisitionModel(napari_viewer)
        self.acquisition_view = AcquisitionView()
        self.acquisition_controller = AcquisitionController(self.acquisition_view, self.acquisition_model)
        self.insertTab(0, self.acquisition_view, "Acquisition")
        
        self.draw_rois_model = DrawROIsModel(napari_viewer)
        self.targeting_view = TargetingView()
        self.targeting_controller = TargetingController(self.targeting_view, self.draw_rois_model)
        self.insertTab(1, self.targeting_view, "Targeting")

        stack_viewer = StackViewer(napari.Viewer(show=False), parent=self)
        self.registration_model = RegistrationModel(napari_viewer, stack_viewer)
        self.registration_view = RegistrationView()
        self.registration_controller = RegistrationController(self.registration_view, self.registration_model)
        self.insertTab(2, self.registration_view, "Registration")
        
        self.acquisition_model.live_viewer.initialized.connect(self.registration_model.add_fixed_image)
        self.acquisition_model.live_viewer.cleared.connect(self.registration_model.remove_fixed_image)
        self.draw_rois_model.targeting_layer_added.connect(self.registration_model.add_moving_image)
        self.draw_rois_model.targeting_layer_removed.connect(self.registration_model.remove_moving_image)
        # connect add ROI event to add an ROI layer to the registration model
        self.draw_rois_model.labels_added.connect(self.registration_model.align_planes_model.add_labels_layer)
        self.draw_rois_model.labels_removed.connect(self.registration_model.align_planes_model.remove_labels_layer)
        self.registration_model.align_planes_model.rotation_finished.connect(lambda m: self.draw_rois_model.enable_editing(m is None))
        