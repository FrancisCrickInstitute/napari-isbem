import napari
from qtpy.QtWidgets import QVBoxLayout, QVBoxLayout, QTabWidget

from napari_sbem_viewer._controllers import RegistrationController, AcquisitionController, TargetingController
from napari_sbem_viewer._models import AcquisitionModel, RegistrationModel, DrawROIsModel, StackViewer, LayerModel
from napari_sbem_viewer._views import AcquisitionView, RegistrationView, TargetingView


class SBEMViewerWidget(QTabWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        
        self.layer_model = LayerModel(napari_viewer)

        self.acquisition_model = AcquisitionModel(napari_viewer)
        self.acquisition_view = AcquisitionView()
        self.acquisition_controller = AcquisitionController(self.acquisition_view, self.acquisition_model, self.layer_model)
        self.insertTab(0, self.acquisition_view, "Acquisition")
        
        self.draw_rois_model = DrawROIsModel(napari_viewer)
        self.targeting_view = TargetingView()
        self.targeting_controller = TargetingController(self.targeting_view, self.draw_rois_model, self.layer_model)
        self.insertTab(1, self.targeting_view, "Targeting")

        stack_viewer = StackViewer(napari.Viewer(show=False), parent=self)
        self.registration_model = RegistrationModel(napari_viewer, stack_viewer)
        self.registration_view = RegistrationView()
        self.registration_controller = RegistrationController(self.registration_view, self.registration_model, self.layer_model)
        self.insertTab(2, self.registration_view, "Registration")
        
        self.acquisition_model.live_viewer.initialized.connect(self.layer_model.add_em_layer)
        self.acquisition_model.live_viewer.cleared.connect(self.layer_model.remove_em_layer)
        self.registration_model.align_planes_model.rotation_finished.connect(lambda m: self.draw_rois_model.enable_editing(m is None))
        