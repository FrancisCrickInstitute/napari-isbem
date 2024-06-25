import napari
from qtpy.QtWidgets import QPushButton, QGridLayout, QLabel, QSpinBox, QGroupBox, QCheckBox, QMessageBox, QWidget

from napari_sbem_viewer._widgets.registration import PointSelection
from napari_sbem_viewer._utils.registration_utils import get_transformation_matrix_slices


class ManualRegistration(QWidget):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__(parent=parent)
        
        self.setMinimumWidth(180)
        self.viewer = viewer
        self.setLayout(QGridLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.layout().addWidget(QLabel("Fixed layer"), 0, 0)
        self.fixed_z_slice_spinbox = QSpinBox(maximum=10000)
        self.layout().addWidget(self.fixed_z_slice_spinbox, 0, 1)
        self.layout().addWidget(QLabel("Matching moving layer"), 1, 0)
        self.moving_z_slice_spinbox = QSpinBox(maximum=10000)
        self.layout().addWidget(self.moving_z_slice_spinbox, 1, 1)
        self.reverse_checkbox = QCheckBox("Reverse Z direction")
        self.layout().addWidget(self.reverse_checkbox, 2, 0, 1, 2)
        self.transform_3d_checkbox = QCheckBox("3D transform")
        self.layout().addWidget(self.transform_3d_checkbox, 3, 0, 1, 2)
        
        # Fixed image points
        self.fixed_points_widget = PointSelection(
            self.viewer, 
            self.fixed_z_slice_spinbox,
            name='Fixed image points', 
            points_layer_config={'symbol': 'cross', 'face_color': 'blue'})
        self.layout().addWidget(self.fixed_points_widget, 4, 0, 1, 2)
        
        # Moving image points
        self.moving_points_widget = PointSelection(
            self.viewer, 
            self.moving_z_slice_spinbox,
            name='Moving image points', 
            points_layer_config={'symbol': 'x', 'face_color': 'red'}
            )
        self.layout().addWidget(self.moving_points_widget, 5, 0, 1, 2)
        
        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self._on_click_manual_register)
        self.layout().addWidget(self.register_button, 6, 0, 1, 2)
        
        self.parentWidget().parentWidget().select_images.moving_combo_box.currentTextChanged.connect(self._on_select_moving_image)
        self.parentWidget().parentWidget().select_images.fixed_combo_box.currentTextChanged.connect(self._on_select_fixed_image)
        
    def get_moving_points(self):
        layer = self.moving_points_widget.points_layer
        if layer is not None:
            return layer.data.copy()
        
    def get_fixed_points(self):
        layer = self.fixed_points_widget.points_layer
        if layer is not None:
            return layer.data.copy()

    def _on_click_manual_register(self):
        self.register_button.setEnabled(False)
        moving_layer = self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()
        fixed_layer = self.parentWidget().parentWidget().parentWidget().select_images.get_fixed_layer()
        if moving_layer is None or fixed_layer is None:
            raise ValueError("Select a moving image and a fixed image")
        
        reverse = self.reverse_checkbox.isChecked()
        
        fixed_slice = self.fixed_z_slice_spinbox.value()
        moving_slice = self.moving_z_slice_spinbox.value()
            
        # calculate the z-offset in physical units
        if reverse:
            # if reversing the z-axis, the moving layer slice becomes z_shape - moving_slice.
            # additionally, after flipping the z-axis, the moving image must be shifted up by z_shape
            # i.e. moving_layer.data.shape[0] - moving_slice - moving_layer.data.shape[0], and so it simplifies to
            z_offset = -moving_slice * moving_layer.scale[0] - fixed_slice * fixed_layer.scale[0]
        else:
            z_offset = moving_slice * moving_layer.scale[0] - fixed_slice * fixed_layer.scale[0]
            
        # get the points for the affine transform if they exist
        pts_moving = self.get_moving_points()
        pts_fixed = self.get_fixed_points()
        
        if pts_moving is not None and pts_fixed is not None:
            if len(pts_fixed) != len(pts_moving):
                QMessageBox.warning(self, "Invalid points", "Number of fixed and moving points must be equal")
                self._reset_ui()
                return
            if len(pts_fixed) < 3 and len(pts_moving) < 3:
                QMessageBox.warning(self, "Invalid points", "Select at least 3 points for the transformation")
                self._reset_ui()
                return
        if self.transform_3d_checkbox.isChecked():
            raise NotImplementedError("3D transformation not implemented")
            # T = get_transformation_matrix_3d(reverse, z_offset, pts_fixed, pts_moving, scale=None)
        else:
            T = get_transformation_matrix_slices(reverse, z_offset, pts_fixed, pts_moving, scale=None)
            
        moving_layer.affine = T
            
        # reset the z-depth slider
        self.viewer.dims.set_point(0, fixed_layer.data_to_world((fixed_slice, 0, 0))[0])
        
        # enable the register button
        self._reset_ui()
        
    def _reset_ui(self):
        self.register_button.setEnabled(True)
        self.fixed_points_widget.stack_viewer.hide()
        self.moving_points_widget.stack_viewer.hide()
        
    def _on_select_moving_image(self):
        self.moving_points_widget._on_change_image_layer(self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer())
        
    def _on_select_fixed_image(self):
        self.fixed_points_widget._on_change_image_layer(self.parentWidget().parentWidget().parentWidget().select_images.get_fixed_layer())
        