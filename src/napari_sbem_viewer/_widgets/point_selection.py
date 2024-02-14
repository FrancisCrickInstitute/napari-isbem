from typing import Optional, Dict

import napari
from napari.layers.base._base_constants import ActionType
import numpy as np
from qtpy.QtWidgets import QPushButton, QListWidget, QWidget, QGridLayout, QLabel, QAbstractScrollArea, QMessageBox, QSpinBox

from napari_sbem_viewer._widgets.stack_viewer import StackViewer


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
        self.stack_viewer = StackViewer(napari.Viewer(show=False), points_layer_config, self)

        self.points_layer_config = points_layer_config
        self.setLayout(QGridLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.layout().addWidget(QLabel(name), 0, 0, 1, 2)
        self.points_list_widget = QListWidget()
        self.points_list_widget.currentItemChanged.connect(self._on_select_point)
        self.layout().addWidget(self.points_list_widget, 1, 0, 1, 2)
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._on_click_add)
        self.layout().addWidget(self.add_button, 2, 0)
        self.remove_button = QPushButton("Remove", enabled=False)
        self.remove_button.clicked.connect(self._on_click_remove)
        self.layout().addWidget(self.remove_button, 2, 1)
        
        self.points_list_widget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.stack_viewer.viewer.layers.events.removed.connect(self._on_remove_points_layer)

        
    @property
    def points_layer(self):
        return self.stack_viewer.points_layer
        
    def _on_click_add(self):
        if self.stack_viewer.image_layer is None:
            QMessageBox.warning(self, "No image layer selected", "Select an image layer first")
            return
        
        self.stack_viewer.show()
        if self.stack_viewer.points_layer is None:
            self.stack_viewer.add_points_layer()
            layer = self.stack_viewer.points_layer
            layer.events.data.connect(self._on_update_points)

        # select the points layer and set to add mode
        self.stack_viewer.activate_points_layer()
        
    def _on_click_remove(self):
        selected_row = self.points_list_widget.currentRow()
        points_layer = self.stack_viewer.points_layer
        
        # if no row is selected, do nothing
        if selected_row == -1:
            return
        
        # remove the selected_row from napari
        points_list = points_layer.data
        points_list = np.delete(points_list, selected_row, axis=0)
        points_layer._set_data(points_list)
        
        # remove the selected_row from the points list
        self.points_list_widget.takeItem(selected_row)
        
        if not len(points_list):
            return
        
        # highlight the correct new point
        if selected_row < len(points_list):
            new_selected_row = selected_row
        else:
            new_selected_row = selected_row - 1
            
        points_layer.selected_data = [new_selected_row]
        
    def _on_select_point(self, item):
        current_row = self.points_list_widget.row(item)
        
        if current_row == -1:
            self.remove_button.setEnabled(False)
            return
        
        points_layer = self.stack_viewer.points_layer
        
        # highlight the current point in the viewer
        if current_row < len(points_layer.data):
            points_layer.selected_data = [current_row]
            points_layer._set_highlight(force=True)
            
        self.remove_button.setEnabled(True)
        
    def _on_update_points(self, event):
        """
        Called when the points layer is updated by either adding or removing
        points directly in the viewer.
        """
        points_layer = self.stack_viewer.points_layer
        if event.action == ActionType.ADDED:
            self.points_list_widget.addItem(str(points_layer.data[-1]))
            self.layer_spinbox.setValue(int(self.stack_viewer.viewer.dims.current_step[0]))
        if event.action == ActionType.REMOVED:
            self.points_list_widget.takeItem(event.data_indices[0])
            self.points_list_widget.setCurrentRow(-1)
            
    def _on_remove_points_layer(self, event):
        if event.value.name == self.stack_viewer.points_layer_name:
            self.points_list_widget.clear()
        
    def _get_layer(self, layer_name):
        for layer in self.stack_viewer.layers:
            if layer.name == layer_name: 
                return layer
        return None