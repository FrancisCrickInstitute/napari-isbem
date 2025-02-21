import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout

from napari_sbem_viewer._views.rois import AddTargetingImage, AddLabels, LabelSettings
from napari_sbem_viewer._models import DrawROIsModel
from napari_sbem_viewer._controllers import DrawROIsController


class DrawROIsWidget(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        
        self.add_targeting_image = AddTargetingImage(parent=self)
        self.add_labels = AddLabels(parent=self)
        self.label_settings = LabelSettings(parent=self)
        self.draw_rois_model = DrawROIsModel(self.viewer)
        self.draw_rois_controller = DrawROIsController(
            self.draw_rois_model,
            self.add_targeting_image,
            self.add_labels,
            self.label_settings
        )

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.add_targeting_image)
        self.layout().addWidget(self.add_labels)
        self.layout().addWidget(self.label_settings)
        self.layout().addStretch(1)
        