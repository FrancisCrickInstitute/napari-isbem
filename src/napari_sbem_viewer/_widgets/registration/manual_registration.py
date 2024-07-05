import functools
import os
from enum import Enum

import napari
from napari.layers.base._base_constants import Mode
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
        self.initial_transform = None
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.upload_transform_button = QPushButton("Upload transform")
        self.upload_transform_button.clicked.connect(self._on_click_upload_transform)
        self.layout().addWidget(self.upload_transform_button, 0, 0, 1, 2)
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self._on_click_start)
        self.layout().addWidget(self.start_button, 1, 0, 1, 2)

        self.reverse_checkbox = QCheckBox("Reverse Z direction")
        self.reverse_checkbox.stateChanged.connect(self._flip_z)
        self.reverse_checkbox.setEnabled(False)
        self.layout().addWidget(self.reverse_checkbox, 2, 0, 1, 2)
        
        self.move_down_button = QPushButton("Move down")
        self.move_down_button.clicked.connect(functools.partial(self._offset_z, 1))
        self.move_down_button.setEnabled(False)
        self.layout().addWidget(self.move_down_button, 3, 0)
        self.move_up_button = QPushButton("Move up")
        self.move_up_button.clicked.connect(functools.partial(self._offset_z, -1))
        self.move_up_button.setEnabled(False)
        self.layout().addWidget(self.move_up_button, 3, 1)
        
        model_layout = QHBoxLayout()
        self.model_combobox = QComboBox()
        self.model_combobox.addItems([str(model.name) for model in AffineTransformChoices])
        self.model_combobox.setEnabled(False)
        self.model_label = QLabel("Model:")
        self.model_label.setEnabled(False)
        model_layout.addWidget(self.model_label)
        model_layout.addWidget(self.model_combobox)
        model_layout.setStretch(1, 1)
        self.layout().addLayout(model_layout, 4, 0, 1, 2)
    
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._on_click_save)
        self.save_button.setEnabled(False)
        self.layout().addWidget(self.save_button, 5, 0)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_click_cancel)
        self.cancel_button.setEnabled(False)
        self.layout().addWidget(self.cancel_button, 5, 1)
        
        self.layout().setRowStretch(self.layout().rowCount(), 1)
        
    @property
    def fixed_image_layer(self):
        return self.parentWidget().parentWidget().parentWidget().select_images.get_fixed_layer()
    
    @property
    def moving_image_layer(self):
        return self.parentWidget().parentWidget().parentWidget().select_images.get_moving_layer()
    
    def _on_click_cancel(self):
        moving_points_layer = self.points_layers[1]
        self.reverse_checkbox.setChecked(False)
        if self.moving_image_layer is not None:
            self.moving_image_layer.affine = None
        if moving_points_layer is not None:
            moving_points_layer.affine = None

    def _offset_z(self, offset):
        moving_points_layer = self.points_layers[1]
        if self.moving_image_layer is not None:
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
        self.initial_transform = self.moving_image_layer.affine
        self.moving_image_layer.mode = Mode.TRANSFORM
        self.moving_image_layer.events.affine.connect(self._affine_callback)
        
        # focus on the fixed layer
        # reset_view(self.viewer, self.moving_image_layer)

        self._create_points_layers()
        pts_layer0 = self.points_layers[0]
        pts_layer1 = self.points_layers[1]
        pts_layer0.events.data.connect(self._next_layer_callback)
        pts_layer1.events.data.connect(self._next_layer_callback)

        # get the layer order started
        for layer in [self.fixed_image_layer, pts_layer0, self.moving_image_layer, pts_layer1]:
            self.viewer.layers.move(self.viewer.layers.index(layer), -1)

        self.viewer.layers.selection.active = pts_layer1
        pts_layer1.mode = 'add'

        self._enable_ui()

    def _enable_ui(self):
        self.start_button.setEnabled(False)
        self.save_button.setEnabled(True)
        self.move_up_button.setEnabled(True)
        self.move_down_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.reverse_checkbox.setEnabled(True)
        self.model_combobox.setEnabled(True)
        self.model_label.setEnabled(True)
        
    def _disable_ui(self):        
        self.start_button.setEnabled(True)
        self.save_button.setEnabled(False)
        self.move_up_button.setEnabled(False)
        self.move_down_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.reverse_checkbox.setEnabled(False)
        self.model_combobox.setEnabled(False)
        self.model_label.setEnabled(False)       
            
    def _on_stop(self):
        self._disable_ui()
        self.moving_image_layer.mode = Mode.PAN_ZOOM
        if self.delete_pts:
            self._remove_points_layers()
        else:
            self._reset_points_layers()
            
    def _reset_points_layers(self):
        for layer in self.points_layers:
            layer.events.data.disconnect(self._next_layer_callback)
            layer.events.affine.disconnect(self._affine_callback)
            layer.mode = 'pan_zoom'
    
    def _remove_points_layers(self):
        for layer in self.points_layers:
            self.viewer.layers.remove(layer)
            
    def _on_click_save(self):
        self._save_transform(self.moving_image_layer.affine.affine_matrix)
        self._on_stop()
        
    def _on_click_cancel(self):
        self.moving_image_layer.affine = self.initial_transform
        self._on_stop()
        
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
    
    def _affine_callback(self, event):
        moving_points_layer = self.points_layers[1]
        moving_points_layer.affine = convert_affine_to_ndims(
            self.moving_image_layer.affine.affine_matrix, moving_points_layer.ndim
            )
        
    def _next_layer_callback(self):
        fixed_points_layer, moving_points_layer = self.points_layers
        pts0, pts1 = fixed_points_layer.data, moving_points_layer.data
        ndim_raw = pts0.shape[1]  # shape of raw points
        pts0, pts1 = pts0[:, -2:], pts1[:, -2:]
        n0, n1 = len(pts0), len(pts1)
        ndim = pts0.shape[1]  # shape of points after potentially changing to 2D
        if moving_points_layer in self.viewer.layers.selection:
            if n1 < ndim + 1:
                return
            if n1 == ndim + 1:
                reset_view(self.viewer, self.fixed_image_layer)
            if n1 > n0:
                self.viewer.layers.selection.active = fixed_points_layer
                self.viewer.layers.move(self.viewer.layers.index(self.fixed_image_layer), -1)
                self.viewer.layers.move(self.viewer.layers.index(fixed_points_layer), -1)
                fixed_points_layer.mode = 'add'
        elif fixed_points_layer in self.viewer.layers.selection:
            if n0 == n1:
                # we just added enough points:
                # estimate transform, go back to layer0
                if n1 > ndim:
                    mat = calculate_transform(
                            pts0, pts1, ndim, model_class=AffineTransformChoices[self.model_combobox.currentText()].value,
                            )
                    # if image is 3D, add z-shift to 2D transform
                    if ndim_raw > 2:
                        z_mat = calculate_z_transform(fixed_points_layer, moving_points_layer, self.reverse_checkbox.isChecked())
                        mat = z_mat @ convert_affine_to_ndims(mat, ndim_raw)
                    ref_mat = self.fixed_image_layer.affine.affine_matrix
                    # must shrink ndims of affine matrix if dims of image layer is bigger than moving layer #####
                    if self.fixed_image_layer.ndim > self.moving_image_layer.ndim:
                        ref_mat = convert_affine_to_ndims(
                                ref_mat, self.moving_image_layer.ndim
                                )
                    # must pad affine matrix with identity matrix if dims of moving layer smaller #####
                    self.moving_image_layer.affine = convert_affine_to_ndims(
                            (ref_mat @ mat), self.moving_image_layer.ndim
                            )
                    moving_points_layer.affine = convert_affine_to_ndims(
                            (ref_mat @ mat), moving_points_layer.ndim
                            )
                self.viewer.layers.selection.active = moving_points_layer
                fixed_points_layer.mode = 'add'
                self.viewer.layers.move(self.viewer.layers.index(self.moving_image_layer), -1)
                self.viewer.layers.move(self.viewer.layers.index(moving_points_layer), -1)
                reset_view(self.viewer, self.moving_image_layer)
                
                
class AffineTransformChoices(Enum):
    Affine = AffineTransform
    Euclidean = EuclideanTransform
    Similarity = SimilarityTransform