import napari
from qtpy.QtWidgets import QTabWidget, QVBoxLayout

from napari_isbem._controllers import (
    AcquisitionController,
    RegistrationController,
    TargetingController,
)
from napari_isbem._models import (
    AcquisitionModel,
    LayerModel,
    RegistrationModel,
    StackViewer,
    TargetingModel,
)
from napari_isbem._views import (
    AcquisitionView,
    RegistrationView,
    TargetingView,
)


class iSBEMWidget(QTabWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())

        self.layer_model = LayerModel(napari_viewer)

        self.targeting_model = TargetingModel(napari_viewer, self.layer_model)
        self.targeting_view = TargetingView()
        self.targeting_controller = TargetingController(
            self.targeting_view, self.targeting_model
        )
        self.insertTab(0, self.targeting_view, 'Targeting')

        self.acquisition_model = AcquisitionModel(
            napari_viewer, self.layer_model
        )
        self.acquisition_view = AcquisitionView()
        self.acquisition_controller = AcquisitionController(
            self.acquisition_view, self.acquisition_model
        )
        self.insertTab(1, self.acquisition_view, 'Acquisition')

        stack_viewer = StackViewer(napari.Viewer(show=False), parent=self)
        self.registration_model = RegistrationModel(
            napari_viewer, stack_viewer, self.layer_model
        )
        self.registration_view = RegistrationView()
        self.registration_controller = RegistrationController(
            self.registration_view, self.registration_model
        )
        self.insertTab(2, self.registration_view, 'Registration')

        self.registration_model.align_planes_model.rotation_finished.connect(
            lambda m: self.targeting_model.enable_editing(m is None)
        )
