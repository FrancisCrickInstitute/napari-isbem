import functools
from enum import Enum

import napari
from napari.layers.base._base_constants import Mode, ActionType
from qtpy.QtWidgets import QGridLayout, QPushButton, QFileDialog, QHBoxLayout, QHBoxLayout, QComboBox, QLabel, QCheckBox, QWidget, QMessageBox
import numpy as np
from skimage.transform import (
        AffineTransform,
        EuclideanTransform,
        SimilarityTransform,
        )

from napari_sbem_viewer._utils.registration_utils import (flip_transform_matrix, 
                                                          offset_transform_matrix_z,
                                                          calculate_transform, 
                                                          calculate_z_transform, 
                                                          convert_affine_to_ndims,
                                                          is_2d_affine_matrix)
from napari_sbem_viewer._utils.general_utils import reset_view


class ManualRegistration(QWidget):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__(parent=parent)
        
        self.setMinimumWidth(180)
        self.viewer = viewer
        self.setLayout(QGridLayout())
        self.delete_pts = True
        self.points_layers = [None, None]
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.upload_transform_button = QPushButton("Upload transform")
        self.upload_transform_button.clicked.connect(self._on_click_upload_transform)
        self.layout().addWidget(self.upload_transform_button, 0, 0, 1, 2)
        
        self.save_button = QPushButton("Save transform")
        self.save_button.clicked.connect(self._on_click_save)
        self.layout().addWidget(self.save_button, 1, 0)
        
        self.save_button = QPushButton("Reset transform")
        self.save_button.clicked.connect(self._on_click_reset)
        self.layout().addWidget(self.save_button, 1, 1)
        
        # ----------------- Z adjustment -----------------
        self.layout().addWidget(QLabel("Adjust Z:"), 2, 0, 1, 2)
        self.reverse_checkbox = QCheckBox("Reverse Z direction")
        self.reverse_checkbox.stateChanged.connect(self._flip_z)
        self.layout().addWidget(self.reverse_checkbox, 3, 0, 1, 2)
        
        self.move_down_button = QPushButton("Move down")
        self.move_down_button.clicked.connect(functools.partial(self._offset_z, 1))
        self.layout().addWidget(self.move_down_button, 4, 0)
        self.move_up_button = QPushButton("Move up")
        self.move_up_button.clicked.connect(functools.partial(self._offset_z, -1))
        self.layout().addWidget(self.move_up_button, 4, 1)
        
        # ----------------- 2D transform -----------------
        self.layout().addWidget(QLabel("2D Transform:"), 5, 0, 1, 2)
        
        self.toggle_manual_adjustment_button = QPushButton("Toggle manual adjustment")
        self.toggle_manual_adjustment_button.clicked.connect(self._on_toggle_manual_adjustment)
        self.layout().addWidget(self.toggle_manual_adjustment_button, 6, 0, 1, 2)
            
        model_layout = QHBoxLayout()
        self.model_combobox = QComboBox()
        self.model_combobox.addItems([str(model.name) for model in AffineTransformChoices])
        self.model_combobox.currentIndexChanged.connect(self._do_transform)
        self.model_label = QLabel("Model:")
        model_layout.addWidget(self.model_label)
        model_layout.addWidget(self.model_combobox)
        model_layout.setStretch(1, 1)
        self.layout().addLayout(model_layout, 7, 0, 1, 2)
        
        self.remove_outliers_checkbox = QCheckBox("Remove outliers")
        self.remove_outliers_checkbox.stateChanged.connect(self._do_transform)
        self.layout().addWidget(self.remove_outliers_checkbox, 8, 0, 1, 2)
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self._on_click_start)
        self.layout().addWidget(self.start_button, 9, 0)
    
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_click_stop)
        self.stop_button.setEnabled(False)
        self.layout().addWidget(self.stop_button, 9, 1)
        
        self.layout().setRowStretch(self.layout().rowCount(), 1)
        
    @property
    def fixed_image_layer(self):
        return self.parentWidget().parentWidget().parentWidget().select_images.get_fixed_layer()
    
    @property
    def moving_image_layer(self):
        return self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()

    def _offset_z(self, offset):
        moving_points_layer = self.points_layers[1]
        if self.moving_image_layer is not None:
            current_z = self.viewer.dims.point[0]
            mat = convert_affine_to_ndims(self.moving_image_layer.affine.affine_matrix, 3)
            offset_transform_matrix_z(mat, offset)
            ref_mat = convert_affine_to_ndims(self.fixed_image_layer.affine.affine_matrix, 3)
            self.moving_image_layer.affine = convert_affine_to_ndims(
                    (ref_mat @ mat), self.moving_image_layer.ndim
                    )
            if moving_points_layer is not None:
                moving_points_layer.affine = convert_affine_to_ndims(
                        (ref_mat @ mat), moving_points_layer.ndim
                        )
            self.viewer.dims.set_point(0,  current_z)
                
    def _flip_z(self):
        moving_points_layer = self.points_layers[1]
        if self.moving_image_layer is not None:
            mat = convert_affine_to_ndims(self.moving_image_layer.affine.affine_matrix, 3) 
            mat = flip_transform_matrix(mat, self.moving_image_layer.data.shape[-3] * self.moving_image_layer.scale[-3])
            ref_mat = convert_affine_to_ndims(self.fixed_image_layer.affine.affine_matrix, 3)
            self.moving_image_layer.affine = convert_affine_to_ndims(
                    (ref_mat @ mat), self.moving_image_layer.ndim
                    )           
            if moving_points_layer is not None:
                moving_points_layer.affine = convert_affine_to_ndims(
                        (ref_mat @ mat), moving_points_layer.ndim
                        )
                
    def _create_points_layers(self):
        # set points layer for each image
        # Use C0 and C1 from matplotlib color cycle
        points_layers_to_add = [(self.fixed_image_layer, (0.122, 0.467, 0.706, 1.0)),
                                (self.moving_image_layer, (1.0, 0.498, 0.055, 1.0))]

        # make points layer if it was not specified
        estimation_ndim = min(self.fixed_image_layer.ndim, self.moving_image_layer.ndim)
        for i in range(len(self.points_layers)):
            if self.points_layers[i] not in self.viewer.layers:
                layer, color = points_layers_to_add[i]
                new_layer = self.viewer.add_points(
                        ndim=estimation_ndim, # ndims of all points layers same lowest ndim of fixed or moving
                        name=layer.name + '_pts',
                        affine=convert_affine_to_ndims(
                                layer.affine, estimation_ndim
                                ),
                        face_color=[color],
                        )
                self.points_layers[i] = new_layer
                
    def _on_click_upload_transform(self):
        options = QFileDialog.Options()
        if not self.moving_image_layer:
            QMessageBox.critical(self, "Error", "No moving image layer selected")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, 
                                                   "Open File", 
                                                   "", 
                                                   "Text Files (*.txt);;All Files (*)", 
                                                   options=options)
        if file_path:
            try:
                transform = np.loadtxt(file_path, delimiter=',')
                if not is_2d_affine_matrix(transform):
                    raise ValueError("Transform must be a 2D affine transform")
                self.moving_image_layer.affine = convert_affine_to_ndims(
                    transform, 
                    self.moving_image_layer.ndim
                    )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
        
    def _on_click_start(self):
        self.moving_image_layer.events.affine.connect(self._affine_callback)

        self._create_points_layers()
        pts_layer0 = self.points_layers[0]
        pts_layer1 = self.points_layers[1]
        pts_layer0.events.data.connect(self._next_layer_callback)
        pts_layer1.events.data.connect(self._next_layer_callback)

        # get the layer order started
        for layer in [self.fixed_image_layer, pts_layer0, self.moving_image_layer, pts_layer1]:
            self.viewer.layers.move(self.viewer.layers.index(layer), -1)

        self._focus_fixed_layer()
        self._enable_ui()
        
    def _on_toggle_manual_adjustment(self):
        if self.moving_image_layer.mode != Mode.TRANSFORM:
            self.moving_image_layer.mode = Mode.TRANSFORM
            self.viewer.layers.selection.active = self.moving_image_layer
        else:
            self.moving_image_layer.mode = Mode.PAN_ZOOM

    def _enable_ui(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
    def _disable_ui(self):        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
            
    def _on_click_stop(self):
        self._disable_ui()
        self.moving_image_layer.mode = Mode.PAN_ZOOM
        self.moving_image_layer.events.affine.disconnect(self._affine_callback)
        if self.delete_pts:
            self._remove_points_layers()
        else:
            self._reset_points_layers()
            
    def _reset_points_layers(self):
        for layer in self.points_layers:
            layer.events.data.disconnect(self._next_layer_callback)
            layer.mode = 'pan_zoom'
    
    def _remove_points_layers(self):
        for layer in self.points_layers:
            self.viewer.layers.remove(layer)
        self.points_layers = [None, None]
            
    def _on_click_save(self):
        self._save_transform(self.moving_image_layer.affine.affine_matrix)
        
    def _on_click_reset(self):
        reply = QMessageBox.question(self, 'Confirmation',
                                     'Are you sure you want to reset the transformation?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.moving_image_layer.affine = None
        
        
    def _save_transform(self, affine_matrix):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, 
                                                   "Save File", 
                                                   "", 
                                                   "Text Files (*.txt);;All Files (*)", 
                                                   options=options)
        if file_path:
            try:
                np.savetxt(file_path, np.asarray(affine_matrix), delimiter=',')
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
    
    def _affine_callback(self):
        moving_points_layer = self.points_layers[1]
        moving_points_layer.affine = convert_affine_to_ndims(
            self.moving_image_layer.affine.affine_matrix, moving_points_layer.ndim
            )
    
    def _focus_fixed_layer(self, reset_camera=True):
        fixed_points_layer = self.points_layers[0]
        self.viewer.layers.selection.active = fixed_points_layer
        self.viewer.layers.move(self.viewer.layers.index(self.fixed_image_layer), -1)
        self.viewer.layers.move(self.viewer.layers.index(fixed_points_layer), -1)
        fixed_points_layer.mode = 'add'
        if reset_camera:
            reset_view(self.viewer, self.fixed_image_layer)
        if len(fixed_points_layer.data):
            z_height = fixed_points_layer.data[-1][0]
            self.viewer.dims.set_point(0, z_height)
        
    def _focus_moving_layer(self, reset_camera=True):
        moving_points_layer = self.points_layers[1]
        self.viewer.layers.selection.active = moving_points_layer
        self.viewer.layers.move(self.viewer.layers.index(self.moving_image_layer), -1)
        self.viewer.layers.move(self.viewer.layers.index(moving_points_layer), -1)
        moving_points_layer.mode = 'add'
        if reset_camera:
            reset_view(self.viewer, self.moving_image_layer)               
        
    def _next_layer_callback(self, event):
        if not event.action == ActionType.ADDED:
            return
        fixed_points_layer, moving_points_layer = self.points_layers
        reset_camera = len(fixed_points_layer.data) < fixed_points_layer.ndim + 1
        if fixed_points_layer in self.viewer.layers.selection:
            self._focus_moving_layer(reset_camera=reset_camera)
        elif moving_points_layer in self.viewer.layers.selection:
            self._do_transform()
            self._focus_fixed_layer(reset_camera=reset_camera)
            
    def _do_transform(self):
        fixed_points_layer, moving_points_layer = self.points_layers
        if self.fixed_image_layer is None or self.moving_image_layer is None:
            return
        if fixed_points_layer is None or moving_points_layer is None:
            return
        pts0, pts1 = fixed_points_layer.data, moving_points_layer.data
        ndim_raw = pts0.shape[1]  # shape of raw points
        pts0, pts1 = pts0[:, -2:], pts1[:, -2:]  
        ndim = pts0.shape[1]  # shape of points after potentially changing to 2D
        if len(pts0) != len(pts1) or len(pts0) <= ndim:
            return
        mat = calculate_transform(
            pts0, 
            pts1, 
            ndim, 
            model_class=AffineTransformChoices[self.model_combobox.currentText()].value,
            remove_outliers=self.remove_outliers_checkbox.isChecked()
            )
        # if image is 3D, add z-shift to 2D transform
        if ndim_raw > 2:
            z_mat = calculate_z_transform(fixed_points_layer, moving_points_layer, self.reverse_checkbox.isChecked())
            mat = z_mat @ convert_affine_to_ndims(mat, ndim_raw)
        ref_mat = self.fixed_image_layer.affine.affine_matrix
        # must shrink ndims of affine matrix if dims of image layer is bigger than moving layer
        if self.fixed_image_layer.ndim > self.moving_image_layer.ndim:
            ref_mat = convert_affine_to_ndims(
                    ref_mat, self.moving_image_layer.ndim
                    )
        # must pad affine matrix with identity matrix if dims of moving layer smaller
        self.moving_image_layer.affine = convert_affine_to_ndims(
                (ref_mat @ mat), self.moving_image_layer.ndim
                )
        moving_points_layer.affine = convert_affine_to_ndims(
                (ref_mat @ mat), moving_points_layer.ndim
                )
                
                
class AffineTransformChoices(Enum):
    Affine = AffineTransform
    Euclidean = EuclideanTransform
    Similarity = SimilarityTransform
    