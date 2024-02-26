from typing import Dict, Optional

import napari
from napari.layers.base._base_constants import ActionType
# from napari.layers.shapes._shapes_constants import Mode
from napari.layers.points._points_constants import Mode
from qtpy.QtWidgets import QGroupBox, QListWidget, QPushButton, QGridLayout
import numpy as np


class ROIList(QGroupBox):
    def __init__(self, 
                 viewer: napari.Viewer,
                 parent):
        super().__init__("ROI Selection")
        self.viewer = viewer
        self.parent = parent
        self.setLayout(QGridLayout())
        # self.shapes_layer = shapes_layer
        
        self.roi_list_widget = QListWidget()
        self.layout().addWidget(self.roi_list_widget, 0, 0, 1, 2)
        
        self.add_button = QPushButton("Add")
        self.layout().addWidget(self.add_button, 1, 0)
        self.remove_button = QPushButton("Remove", enabled=False)
        self.layout().addWidget(self.remove_button, 1, 1)
            
    def _on_update_points(self, event):
        """
        Called when the shapes layer is updated by either adding or removing
        points directly in the viewer.
        """
        roi_layer = self.parent.points_layer
        if event.action == ActionType.ADDED:
            self.roi_list_widget.addItem(f'ROI {len(roi_layer.data)}')
            roi_layer.mode = Mode.ADD
        if event.action == ActionType.REMOVED:
            self.roi_list_widget.takeItem(event.data_indices[0])
            self.roi_list_widget.setCurrentRow(-1)
            

        
        
