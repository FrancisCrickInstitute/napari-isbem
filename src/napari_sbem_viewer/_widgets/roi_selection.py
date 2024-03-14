import napari
from qtpy.QtWidgets import QGroupBox, QWidget, QVBoxLayout
from napari_bbox import BoundingBoxLayer
from napari_bbox.boundingbox.napari_0_4_18._bounding_box_constants import Mode

import numpy as np

from napari_sbem_viewer._widgets import ROIList, StackViewer, SelectROIImage, AdjustROI


class ROISelection(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        self.bbox_layer_config = {'edge_width': 5}
        # self.points_layer = None
        self.bbox_layer = None
        
        # self.select_roi_image = SelectROIImage(self.viewer)
        # self.layout().addWidget(self.select_roi_image)
        
        self.roi_list = ROIList(self.viewer, parent=self)
        self.roi_list.add_button.clicked.connect(self._on_click_add)
        self.roi_list.remove_button.clicked.connect(self._on_click_remove)
        self.roi_list.roi_list_widget.itemClicked.connect(self._on_select_roi_list)
        # self.roi_list.roi_list_widget.currentRowChanged.connect(self._on_change_roi_list)
        self.layout().addWidget(self.roi_list)
        
        # self.adjust_roi = AdjustROI(self.viewer)
        # self.adjust_roi.setVisible(False)
        # self.layout().addWidget(self.adjust_roi)
        # self.adjust_roi.starting_slice.valueChanged.connect(self._on_adjust_roi_starting_z)
        # self.adjust_roi.ending_slice.valueChanged.connect(self._on_adjust_roi_ending_z)
        
        # self.stack_viewer = StackViewer(napari.Viewer(show=False))
        # self.layout().addWidget(self.stack_viewer)
        
        self.viewer.layers.events.removed.connect(self._on_remove_bbox_layer)
        
        self.layout().addStretch(1)
        
    # def _on_change_roi_list(self, item):
    #     if item == -1:
    #         self.adjust_roi.setVisible(False)
    #         return
    #     roi_coords = self.bbox_layer.data[item]
    #     starting_slice = int(self.bbox_layer.data_to_world(roi_coords[0])[0])
    #     ending_slice = int(self.bbox_layer.data_to_world(roi_coords[1])[0])
    #     self.adjust_roi.starting_slice.setValue(starting_slice)
    #     self.adjust_roi.ending_slice.setValue(ending_slice)
    #     self.adjust_roi.setVisible(True)
        
    # def _on_click_remove(self):
    #     selected_row = self.roi_list.roi_list_widget.currentRow()
        
    #     # if no row is selected, do nothing
    #     if selected_row == -1:
    #         return
        
    #     # remove the selected_row from napari
    #     self.bbox_layer.remove_selected()
        
    #     # shapes_list = self.bbox_layer.data
    #     # shapes_list = np.delete(shapes_list, selected_row, axis=0)
    #     # self.bbox_layer._set_data(shapes_list)
        
    #     # remove the selected_row from the shapes list
    #     self.roi_list.roi_list_widget.takeItem(selected_row)

    #     self.roi_list.roi_list_widget.clearSelection()
    #     self.bbox_layer.selected_data = []
    #     # self.viewer.m
        
    def _on_adjust_roi_starting_z(self, value):
        z_data = self.bbox_layer.world_to_data((value, 0, 0))[0]
        self.bbox_layer.data[self.roi_list.roi_list_widget.currentRow()][::2, 0] = z_data
        self.bbox_layer.refresh()
    
    def _on_adjust_roi_ending_z(self, value):
        z_data = self.bbox_layer.world_to_data((value, 0, 0))[0]
        self.bbox_layer.data[self.roi_list.roi_list_widget.currentRow()][1::2, 0] = z_data
        self.bbox_layer.refresh()
          
    def _on_click_add(self):
        if self.bbox_layer is None:
            bounding_box_layer = BoundingBoxLayer(name='ROIs', ndim=3)
            self.bbox_layer = self.viewer.add_layer(bounding_box_layer)
            self.bbox_layer.events.data.connect(self.roi_list._on_update_bbox)
        self.viewer.layers.selection.active = self.bbox_layer
        self.bbox_layer.mode = Mode.ADD_BOUNDING_BOX
            
    def _on_click_remove(self, selected_row):
        selected_row = self.roi_list.roi_list_widget.currentRow()
        # camera_center_z = self.viewer.dims.point[0]
        
        # if no row is selected, do nothing
        if selected_row == -1:
            return
        
        # calculate the current z world coord of the bbox
        z_coord = self.bbox_layer.data_to_world(
            (self.bbox_layer.data[selected_row][0, 0], 0, 0))[0]
        
        self.bbox_layer.selected_data = [selected_row]
        
        # remove the selected_row from napari
        # roi_list = self.bbox_layer.data
        # roi_list = np.delete(roi_list, selected_row, axis=0)
        # self.bbox_layer.data = roi_list
        self.bbox_layer.remove_selected()
        
        # remove the selected_row from the points list
        # self.roi_list.roi_list_widget.takeItem(selected_row)
        
        # remove the highlight from the viewer
        self.bbox_layer.selected_data = []
        self.bbox_layer._set_highlight(force=True)
        
        # reset the z slice of the viewer to the center of the removed ROI
        self.roi_list._reset_z_viewer(z_coord)
        self.roi_list.roi_list_widget.clearSelection()
        
    def _on_remove_bbox_layer(self, event):
        if event.value == self.bbox_layer:
            self.bbox_layer = None
            self.roi_list.roi_list_widget.clear()
            # self.stack_viewer.remove_substack()
        
    def _on_select_roi_list(self, item):
        current_row = self.roi_list.roi_list_widget.row(item)
        
        if current_row == -1:
            self.roi_list.remove_button.setEnabled(False)
            return
        
        # highlight the current point in the viewer
        if current_row < len(self.bbox_layer.data):
            self.bbox_layer.selected_data = [current_row]
            self.bbox_layer._set_highlight(force=True)
            
        center_coords = self.bbox_layer.data_to_world(get_roi_center(self.bbox_layer.data[current_row]))
        self.viewer.camera.center = center_coords
        self.viewer.dims.set_point(0, center_coords[0])
        
        self.bbox_layer.selected_data = [current_row]
        self.bbox_layer._set_highlight(force=True)
        
        self.roi_list.remove_button.setEnabled(True)
        
        
def get_roi_center(coords_list):
    # calculate the min / max values of the x, y and z coordinates
    min_coords = np.min(coords_list, axis=0)
    max_coords = np.max(coords_list, axis=0)
    center_coords = (min_coords + max_coords) / 2
    return center_coords
