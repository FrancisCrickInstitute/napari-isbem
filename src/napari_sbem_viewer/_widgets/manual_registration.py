import napari
from napari.layers.base._base_constants import ActionType
from napari.layers.points._points_constants import Mode
from qtpy.QtWidgets import QPushButton, QGridLayout, QLabel, QSpinBox, QGroupBox, QCheckBox, QProgressBar

from napari_sbem_viewer._widgets import PointSelection


class ManualRegistration(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 ):
        super().__init__("Manual registration")
        
        self.setMinimumWidth(180)
        self.viewer = viewer
        self.setLayout(QGridLayout())
        self.layout().addWidget(QLabel("Fixed layer"), 0, 0)
        self.fixed_z_slice_spinbox = QSpinBox(maximum=10000)
        self.layout().addWidget(self.fixed_z_slice_spinbox, 0, 1)
        self.layout().addWidget(QLabel("Matching moving layer"), 1, 0)
        self.moving_z_slice_spinbox = QSpinBox(maximum=10000)
        self.layout().addWidget(self.moving_z_slice_spinbox, 1, 1)
        self.reverse_checkbox = QCheckBox("Reverse Z direction")
        self.layout().addWidget(self.reverse_checkbox, 2, 0, 1, 2)
        
        # Fixed image points
        self.fixed_points_widget = PointSelection(
            self.viewer, 
            self.fixed_z_slice_spinbox,
            name='Fixed image points', 
            points_layer_config={'symbol': 'cross', 'face_color': 'blue'})
        self.layout().addWidget(self.fixed_points_widget, 3, 0, 1, 2)
        
        # Moving image points
        self.moving_points_widget = PointSelection(
            self.viewer, 
            self.moving_z_slice_spinbox,
            name='Moving image points', 
            points_layer_config={'symbol': 'x', 'face_color': 'red'}
            )
        self.layout().addWidget(self.moving_points_widget, 4, 0, 1, 2)
        
        self.register_button = QPushButton("Register")
        self.layout().addWidget(self.register_button, 5, 0, 1, 2)
        
        self.progress_bar = QProgressBar(value=0)
        self.layout().addWidget(self.progress_bar, 6, 0, 1, 2)
        
    def get_moving_points(self):
        layer = self.moving_points_widget.stack_viewer.points_layer
        if layer is not None:
            return layer.data
        
    def get_fixed_points(self):
        layer = self.fixed_points_widget.stack_viewer.points_layer
        if layer is not None:
            return layer.data
    
    