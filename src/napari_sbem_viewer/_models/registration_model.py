from qtpy.QtCore import QObject, Signal
from napari.layers import Layer
from napari_ome_zarr import napari_get_reader
import numpy as np


from napari_sbem_viewer._models import ManualRegistrationModel, AlignPlanesModel


class RegistrationModel(QObject):
    def __init__(self, viewer, stack_viewer):
        super().__init__()
        self.viewer = viewer
        self.align_planes_model = AlignPlanesModel(self.viewer, stack_viewer)
        self.manual_registration_model = ManualRegistrationModel(self.viewer)
        
    def import_targeting_image(self, file_path):
        reader = napari_get_reader(file_path)
        layer = Layer.create(*reader(file_path)[0])
        self._on_add_moving_image(layer)
        self.viewer.add_layer(layer)
        
    def on_load_live_viewer(self, layer):
        self._on_add_fixed_image(layer)
        
    def _on_add_fixed_image(self, layer):
        self.manual_registration_model.set_fixed_image(layer)
        
    def _on_remove_fixed_image(self):
        self.manual_registration_model.reset()
        
    def _on_add_moving_image(self, layer):
        self.align_planes_model.set_moving_layer(layer)
        self.manual_registration_model.set_moving_image(layer)
        # self._update_reverse_checkbox()
        
    def _on_remove_moving_image(self):
        self.align_planes_model.reset()
        self.manual_registration_model.reset()
        
    def load_transform(self, file_path):
        rotation_matrix = np.loadtxt(file_path, delimiter=',')
        # angle_zy, angle_zx = self.align_planes_model.load_transform(rotation_matrix)
        angle_zy, angle_zx = 0, 0
        self.manual_registration_model.load_transform(rotation_matrix)
        return angle_zy, angle_zx