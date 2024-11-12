from typing import Optional, Dict
from copy import copy

import napari
from napari.qt import QtViewer
from qtpy.QtCore import Qt
from napari.layers.base._base_constants import ActionType
import numpy as np
from qtpy.QtWidgets import QPushButton, QListWidget, QWidget, QGridLayout, QLabel, QAbstractScrollArea, QMessageBox, QSpinBox
from napari.layers.points._points_constants import Mode


class PointSelection(QWidget):
    def __init__(self,
                 viewer: napari.Viewer,
                 layer_spinbox: QSpinBox,
                 name: str,
                 points_layer_config: Optional[Dict[str, str]] = {},
                 ):
        super().__init__()
        
        self.viewer = viewer
        self.layer_spinbox = layer_spinbox
        self.stack_viewer = QtViewer(napari.Viewer(show=False))
        self.stack_viewer.setParent(self)
        self.stack_viewer.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.points_layer = None
        self.image_layer = None

        self.points_layer_config = points_layer_config
        self.setLayout(QGridLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.layout().addWidget(QLabel(name), 0, 0, 1, 2)
        self.points_list_widget = QListWidget()
        self.points_list_widget.itemClicked.connect(self._on_select_point)
        self.layout().addWidget(self.points_list_widget, 1, 0, 1, 2)
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._on_click_add)
        self.layout().addWidget(self.add_button, 2, 0)
        self.remove_button = QPushButton("Remove", enabled=False)
        self.remove_button.clicked.connect(self._on_click_remove)
        self.layout().addWidget(self.remove_button, 2, 1)
        
        self.points_list_widget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.stack_viewer.viewer.layers.events.removed.connect(self._on_remove_points_layer)
        
    # @property
    # def points_layer(self):
    #     return self.stack_viewer.viewer.layers['points']
    
    # def set_image_layer(self, image_layer):
    #     self.image_layer = image_layer
    #     self.add_points_layer()
    #     self.stack_viewer.activate_points_layer()
    #     self.viewer.layers.selection.active = self.points_layer
    #     self.points_layer.mode = Mode.ADD
        
    def _on_change_image_layer(self, image_layer):
        if image_layer != self.image_layer:
            self.image_layer = image_layer
            self.stack_viewer.hide()
            self.stack_viewer.viewer.layers.clear()
            
    def _on_click_add(self):
        if self.image_layer is None:
            QMessageBox.warning(self, "No image layer selected", "Select an image layer first")
            return
        
        # initialise the image layer if not already initialised
        if self.image_layer not in self.stack_viewer.viewer.layers:
            self.stack_viewer.viewer.add_layer(copy(self.image_layer))
        
        # initialise the points layer if not already initialised
        if self.points_layer not in self.stack_viewer.viewer.layers:
            self.points_layer = self.stack_viewer.viewer.add_points(name='points', **self.points_layer_config)
            self.points_layer.events.data.connect(self._on_update_points)
            
        # select the points layer and set to add mode
        self.stack_viewer.viewer.layers.selection.active = self.points_layer
        self.points_layer.mode = Mode.ADD
        self.stack_viewer.show()

    def _on_click_remove(self):
        selected_row = self.points_list_widget.currentRow()
        
        # if no row is selected, do nothing
        if selected_row == -1:
            return
        
        # remove the selected_row from napari
        points_list = self.points_layer.data
        points_list = np.delete(points_list, selected_row, axis=0)
        self.points_layer._set_data(points_list)
        
        # remove the selected_row from the points list
        self.points_list_widget.takeItem(selected_row)

        if not len(points_list):
            return
        
        # highlight the correct new point
        if selected_row < len(points_list):
            new_selected_row = selected_row
        else:
            new_selected_row = selected_row - 1
            
        self.points_layer.selected_data = [new_selected_row]
        
    def _on_select_point(self, item):
        current_row = self.points_list_widget.row(item)
        
        if current_row == -1:
            self.remove_button.setEnabled(False)
            return
        
        # highlight the current point in the viewer
        if current_row < len(self.points_layer.data):
            self.points_layer.selected_data = [current_row]
            self.points_layer._set_highlight(force=True)
            
        self.remove_button.setEnabled(True)
        
    def _on_update_points(self, event):
        """
        Called when the points layer is updated by either adding or removing
        points directly in the viewer.
        """
        if event.action == ActionType.ADDED:
            self.points_list_widget.addItem(str(self.points_layer.data[-1]))
            self.layer_spinbox.setValue(int(self.stack_viewer.viewer.dims.current_step[0]))
        if event.action == ActionType.REMOVED:
            self.points_list_widget.takeItem(event.data_indices[0])
            self.points_list_widget.setCurrentRow(-1)
            
    def _on_remove_points_layer(self, event):
        if event.value.name == 'points':
            self.points_list_widget.clear()
