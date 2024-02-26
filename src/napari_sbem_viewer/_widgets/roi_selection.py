import napari
from qtpy.QtWidgets import QGroupBox, QWidget, QVBoxLayout
# from napari.layers.shapes._shapes_constants import Mode
from napari.layers.points._points_constants import Mode as PointsMode
from napari.layers.shapes._shapes_constants import Mode as ShapesMode

import numpy as np

from napari_sbem_viewer._widgets import ROIList, StackViewer, SelectROIImage


class ROISelection(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.setLayout(QVBoxLayout())
        self.points_layer_config = {'face_color': 'red'}
        self.shapes_layer_config = {'face_color': 'red'}
        self.points_layer = None
        
        self.select_roi_image = SelectROIImage(self.viewer)
        self.layout().addWidget(self.select_roi_image)
        
        self.roi_list = ROIList(self.viewer, parent=self)
        self.roi_list.add_button.clicked.connect(self._on_click_add)
        self.roi_list.remove_button.clicked.connect(self._on_click_remove)
        self.roi_list.roi_list_widget.itemClicked.connect(self._on_select_roi)
        self.layout().addWidget(self.roi_list)
        
        self.stack_viewer = StackViewer(napari.Viewer(show=False))
        self.layout().addWidget(self.stack_viewer)
        
        self.viewer.layers.events.removed.connect(self._on_remove_points_layer)
        
    def _on_click_remove(self):
        selected_row = self.roi_list.roi_list_widget.currentRow()
        
        # if no row is selected, do nothing
        if selected_row == -1:
            return
        
        # remove the selected_row from napari
        points_list = self.points_layer.data
        points_list = np.delete(points_list, selected_row, axis=0)
        self.points_layer._set_data(points_list)
        
        # remove the selected_row from the points list
        self.roi_list.roi_list_widget.takeItem(selected_row)

        self.roi_list.roi_list_widget.clearSelection()
        self.points_layer.selected_data = []
        self.stack_viewer.remove_substack()
        
    def _on_click_add(self):
        if self.points_layer is None:
            self.points_layer = self.viewer.add_points(name='ROIs', ndim=3, **self.points_layer_config)
            self.points_layer.events.data.connect(self.roi_list._on_update_points)
        self.viewer.layers.selection.active = self.points_layer
        self.points_layer.mode = PointsMode.ADD
        
    def _on_remove_points_layer(self, event):
        if event.value == self.points_layer:
            self.points_layer = None
            self.roi_list.roi_list_widget.clear()
            self.stack_viewer.remove_substack()
        
    def _on_select_roi(self, item):
        current_row = self.roi_list.roi_list_widget.row(item)
        
        if current_row == -1:
            self.roi_list.remove_button.setEnabled(False)
            return
        
        # highlight the current point in the viewer
        if current_row < len(self.points_layer.data):
            self.points_layer.selected_data = [current_row]
            self.points_layer._set_highlight(force=True)
            
        center_coords = self.points_layer.data[current_row]
        self.viewer.camera.center = center_coords
        self.viewer.dims.set_point(0, center_coords[0])
        
        image_layer = self.select_roi_image.get_image_layer()
        if image_layer is not None:
            self.stack_viewer.view_substack(image_layer, center_coords)
            self.roi_layer = self.stack_viewer.viewer.add_shapes(name='ROIs', **self.shapes_layer_config)
            self.roi_layer.mode = ShapesMode.ADD_RECTANGLE
        
        self.roi_list.remove_button.setEnabled(True)
        
        
def get_roi_center(coords_list):
    # calculate the min / max values of the x, y and z coordinates
    min_coords = np.min(coords_list, axis=0)
    max_coords = np.max(coords_list, axis=0)
    center_coords = (min_coords + max_coords) / 2
    return center_coords