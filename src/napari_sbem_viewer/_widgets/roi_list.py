from typing import Dict, Optional

import napari
from napari.layers.base._base_constants import ActionType
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
        
    def _reset_z_viewer(self, z: int):
        # reset the z viewer to the z slice of the ROI in world coords
        self.viewer.dims.set_point(0, z)
            
    def _on_update_bbox(self, event):
        """
        Called when the shapes layer is updated by either adding or removing
        ROIs directly in the viewer.
        """
        if not hasattr(event, 'action'):
            return
        bbox_layer = self.parent.bbox_layer
        # if event.action == ActionType.ADDING or event.action == ActionType.REMOVING:
        #     self.current_z_slice = self.viewer.dims.point[0]
        if event.action == ActionType.ADDED:
            if len(bbox_layer.data) < self.roi_list_widget.count():
                return
            # # TODO: change z coord of rectangle to nearest integer so it aligns with overview stack
            self.roi_list_widget.addItem(f'ROI {len(bbox_layer.data)}')
        if event.action == ActionType.REMOVED:
            self.roi_list_widget.takeItem(event.data_indices[0])
        # if event.action == ActionType.REMOVED or event.action == ActionType.ADDED:
        #     self.viewer.dims.set_point(0, self.current_z_slice)        
        #     print(f'set point to {self.current_z_slice}')