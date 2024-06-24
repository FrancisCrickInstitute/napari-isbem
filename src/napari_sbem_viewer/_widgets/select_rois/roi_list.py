import napari
from napari_bbox import BoundingBoxLayer
from napari_bbox.boundingbox.napari_0_4_18._bounding_box_constants import Mode
from napari.layers.base._base_constants import ActionType
from qtpy.QtWidgets import QGroupBox, QListWidget, QPushButton, QGridLayout
import numpy as np


class ROIList(QGroupBox):
    def __init__(self, 
                 viewer: napari.Viewer,
                 parent,
                 bbox_layer_config={}):
        super().__init__("ROI Selection", parent=parent)
        self.viewer = viewer
        self.setLayout(QGridLayout())
        self.bbox_layer_config = bbox_layer_config
        
        self.roi_list_widget = QListWidget()
        self.roi_list_widget.itemClicked.connect(self._on_click_roi_list)
        self.layout().addWidget(self.roi_list_widget, 0, 0, 1, 2)
        
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._on_click_add)
        self.layout().addWidget(self.add_button, 1, 0)
        
        self.remove_button = QPushButton("Remove", enabled=False)
        self.remove_button.clicked.connect(self._on_click_remove)
        self.layout().addWidget(self.remove_button, 1, 1)
        
    @property
    def bbox_layer(self):
        return self.parentWidget().bbox_layer
    
    @bbox_layer.setter
    def bbox_layer(self, bbox_layer):
        self.parentWidget().bbox_layer = bbox_layer
        
    def focus_viewer_on_roi(self, roi_idx):
        center_coords = self.bbox_layer.data_to_world(get_roi_center(self.bbox_layer.data[roi_idx]))
        self.viewer.camera.center = center_coords
        self._reset_z_viewer(center_coords[0])
        
    def _on_click_add(self):
        if self.bbox_layer is None:
            bounding_box_layer = BoundingBoxLayer(name='ROIs', ndim=3, **self.bbox_layer_config)
            self.bbox_layer = self.viewer.add_layer(bounding_box_layer)
            self.bbox_layer.events.data.connect(self._on_update_bbox)
        self.viewer.layers.selection.active = self.bbox_layer
        self.bbox_layer.mode = Mode.ADD_BOUNDING_BOX
            
    def _on_click_remove(self, selected_row):
        selected_row = self.roi_list_widget.currentRow()
        
        # if the selected row is the not the last row, then do nothing
        if selected_row == -1 or selected_row != self.roi_list_widget.count() - 1:
            return
        
        # remove the selected_row from napari
        self.bbox_layer.selected_data = [selected_row]
        self.bbox_layer.remove_selected()
        self.bbox_layer.refresh()
        
    def _reset_z_viewer(self, z: int):
        # reset the z viewer to the z slice of the ROI in world coords
        self.viewer.dims.set_point(0, z)
        
    def _on_click_roi_list(self, item):
        current_row = self.roi_list_widget.row(item)
        
        if current_row == -1:
            self.remove_button.setEnabled(False)
            return

        if current_row == self.roi_list_widget.count() - 1:
            self.remove_button.setEnabled(True)
        else:
            self.remove_button.setEnabled(False)
        
        # highlight the current point in the viewer
        self.focus_viewer_on_roi(current_row)
        self.bbox_layer.selected_data = [current_row]
        self.bbox_layer.refresh()
            
    def _on_update_bbox(self, event):
        """
        Called when the shapes layer is updated by either adding or removing
        ROIs directly in the viewer.
        """
        # event with no action attribute is called when the shape has finished drawing (???) 
        # - use this to focus on the ROI after it has been added.
        if not hasattr(event, 'action'):          
            if hasattr(event, 'data_indices'):
                self._on_click_roi_list(self.roi_list_widget.item(self.roi_list_widget.count() - 1))
            return
        
        if event.action == ActionType.ADDED:
            for i in range(self.roi_list_widget.count(), len(event.value)):
                self.roi_list_widget.addItem(f'ROI {i+1}')
            self.roi_list_widget.setCurrentRow(len(event.value) - 1)
    
        if event.action == ActionType.REMOVED:
            for idx in event.data_indices:
                self._on_remove_bbox(idx)

    def _on_add_bbox(self, idx):
        self.roi_list_widget.addItem(f'ROI {idx}')
        self.roi_list_widget.setCurrentRow(idx)
    
    def _on_remove_bbox(self, idx):
        self.roi_list_widget.takeItem(idx)
        self.roi_list_widget.clearSelection()
        self.roi_list_widget.setCurrentRow(self.roi_list_widget.count() - 1)
        self._on_click_roi_list(self.roi_list_widget.item(self.roi_list_widget.count() - 1))
        
        
def get_roi_center(coords_list):
    # calculate the min / max values of the x, y and z coordinates
    min_coords = np.min(coords_list, axis=0)
    max_coords = np.max(coords_list, axis=0)
    center_coords = (min_coords + max_coords) / 2
    return center_coords
