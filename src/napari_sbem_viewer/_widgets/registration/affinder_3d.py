import functools

import napari
from qtpy.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QSpinBox, QGroupBox, QCheckBox, QMessageBox, QWidget
from affinder.affinder import AffineTransformChoices, close_affinder, remove_pts_layers, convert_affine_to_ndims, reset_view, next_layer_callback

from napari_sbem_viewer._utils.registration_utils import get_z_offset_matrix


class ManualRegistration2(QWidget):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__(parent=parent)
        
        self.setMinimumWidth(180)
        self.viewer = viewer
        self.setLayout(QVBoxLayout())
        self.delete_pts = True
        self.fixed_points = None
        self.moving_points = None
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.layout().addWidget(QLabel("Z-offset:"))
        self.z_offset_spinbox = QSpinBox(maximum=10000, minimum=-10000)
        self.z_offset_spinbox.valueChanged.connect(self._on_z_offset_changed)
        self.layout().addWidget(self.z_offset_spinbox)
        
        self.reverse_checkbox = QCheckBox("Reverse Z direction")
        self.reverse_checkbox.stateChanged.connect(self._on_z_offset_changed)
        self.layout().addWidget(self.reverse_checkbox)

        self.layout().addWidget(QLabel("Model:"))
        self.model_combobox = QComboBox()
        self.model_combobox.addItems([str(model.name) for model in AffineTransformChoices])
        self.layout().addWidget(self.model_combobox)

        self.call_button = QPushButton("Start")
        self.call_button.clicked.connect(self._on_click_call_button)
        self.layout().addWidget(self.call_button)
        
        self.reset_button = QPushButton("Reset transformation")
        self.reset_button.clicked.connect(self._on_click_reset)
        self.layout().addWidget(self.reset_button)
        
        self.layout().addStretch(1)
        
    @property
    def fixed_layer(self):
        return self.parentWidget().parentWidget().parentWidget().select_images.get_fixed_layer()
    
    @property
    def moving_layer(self):
        return self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()
    
    def _on_click_reset(self):
        self.z_offset_spinbox.setValue(0)
        self.reverse_checkbox.setChecked(False)
        if self.moving_layer is not None:
            self.moving_layer.affine = None
        if self.moving_points is not None:
            self.moving_points.affine = None

    def _on_z_offset_changed(self):
        if self.fixed_layer is not None and self.moving_layer is not None:
            z_size_um = self.moving_layer.data.shape[-3] * self.moving_layer.scale[-3]
            # get z offset matrix
            mat_z = get_z_offset_matrix(
                    self.z_offset_spinbox.value(), 
                    self.reverse_checkbox.isChecked(),
                    z_size_um
                    )
            # get existing affine matrix
            mat_affine = convert_affine_to_ndims(convert_affine_to_ndims(self.moving_layer.affine.affine_matrix, 2), 3)
            mat = mat_z @ mat_affine
            ref_mat = convert_affine_to_ndims(self.fixed_layer.affine.affine_matrix, 3)
            self.moving_layer.affine = convert_affine_to_ndims(
                    (ref_mat @ mat), self.moving_layer.ndim
                    )
            if self.moving_points is not None:
                self.moving_points.affine = convert_affine_to_ndims(
                        (ref_mat @ mat), self.moving_points.ndim
                        )
        
    def _on_click_call_button(self):
        mode = self.call_button.text()  # can be "Start" or "Finish"
        if mode == 'Start':
            # focus on the fixed layer
            reset_view(self.viewer, self.fixed_layer)
            # set points layer for each image
            points_layers = [self.fixed_points, self.moving_points]
            # Use C0 and C1 from matplotlib color cycle
            points_layers_to_add = [(self.fixed_layer, (0.122, 0.467, 0.706, 1.0)),
                                    (self.moving_layer, (1.0, 0.498, 0.055, 1.0))]

            # make points layer if it was not specified
            estimation_ndim = min(self.fixed_layer.ndim, self.moving_layer.ndim)
            for i in range(len(points_layers)):
                if points_layers[i] is None:
                    layer, color = points_layers_to_add[i]
                    new_layer = self.viewer.add_points(
                            ndim=estimation_ndim, # ndims of all points layers same lowest ndim of fixed or moving
                            name=layer.name + '_pts',
                            affine=convert_affine_to_ndims(
                                    layer.affine, estimation_ndim
                                    ),
                            face_color=[color],
                            )
                    points_layers[i] = new_layer
            pts_layer0 = points_layers[0]
            pts_layer1 = points_layers[1]
            # make a callback for points added
            callback = next_layer_callback(
                    viewer=self.viewer,
                    reference_image_layer=self.fixed_layer,
                    reference_points_layer=pts_layer0,
                    moving_image_layer=self.moving_layer,
                    moving_points_layer=pts_layer1,
                    reverse_stack=self.reverse_checkbox.isChecked(),
                    do_2d_transform=True,
                    model_class=AffineTransformChoices[self.model_combobox.currentText()].value,
                    output=None
                    )
            pts_layer0.events.data.connect(callback)
            pts_layer1.events.data.connect(callback)

            # get the layer order started
            for layer in [self.moving_layer, pts_layer1, self.fixed_layer, pts_layer0]:
                self.viewer.layers.move(self.viewer.layers.index(layer), -1)

            self.viewer.layers.selection.active = pts_layer0
            pts_layer0.mode = 'add'

            self.close = functools.partial(
                    close_affinder, points_layers, callback
                    )
            self.remove_points_layers = functools.partial(
                    remove_pts_layers, self.viewer, points_layers
                    )
            # change the button/mode for next run
            self.call_button.setText('Finish')
        else:  # we are in Finish mode
            self.close()
            if self.delete_pts:
                self.remove_points_layers()
            self.call_button.setText('Start')
            