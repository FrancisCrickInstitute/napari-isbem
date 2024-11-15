from qtpy.QtCore import QObject, Signal
from napari.layers import Layer
from napari_bbox import BoundingBoxLayer
from napari_bbox.boundingbox.napari_0_4_18._bounding_box_constants import Mode
from napari.layers.base._base_constants import ActionType
from napari.layers import Labels
import numpy as np

from napari_sbem_viewer._reader import get_labels_reader
from napari_sbem_viewer._utils.general_utils import get_roi_center
from napari_sbem_viewer._utils.image_utils import get_bounding_boxes_from_mask


class SelectROIsModel(QObject):
    bbox_selected = Signal(list)
    bbox_added = Signal(np.ndarray, int)
    bbox_removed = Signal(list)
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.bbox_layer_config = {'edge_width': 5}
        self.bbox_layer = None
        self.adding_bbox = []
        
    def import_labels(self, file_path):
        reader = get_labels_reader(file_path)
        if reader is None:
            raise ValueError("Unsupported file format")
        self.viewer.add_layer(Layer.create(*reader(file_path)[0]))
        
    def add_bboxes_from_labels(self, layer_name):
        labels_layer = self.get_layer(layer_name)
        if labels_layer is None:
            raise ValueError("No labels layer selected")
        if labels_layer.ndim != 3:
            raise ValueError("Labels layer must be 3D")
        self.add_bbox_layer()
        mask = labels_layer.data
        bounding_boxes = get_bounding_boxes_from_mask(mask)
        bounding_boxes_scaled = [
            [labels_layer.data_to_world(coord) for coord in bounding_box]
            for bounding_box in bounding_boxes
        ]
        self.bbox_layer.add(bounding_boxes_scaled)
        
    def select_bboxes(self, indices):
        if not len(indices):
            self.bbox_layer.selected_data = []
            self.bbox_layer.refresh()
            return
        # highlight the current point in the viewer
        self._focus_viewer_on_roi(indices[-1])
        self.bbox_layer.selected_data = indices
        self.bbox_layer.refresh()
        
    def add_bbox_layer(self):
        if self.bbox_layer is None:
            bounding_box_layer = BoundingBoxLayer(name='ROIs', 
                                                  ndim=3, 
                                                  **self.bbox_layer_config)
            self.bbox_layer = self.viewer.add_layer(bounding_box_layer)
            self.bbox_layer.events.data.connect(self._on_update_bbox_layer)
            self.bbox_layer.mouse_drag_callbacks.append(self._on_mouse_move)
        self.viewer.layers.selection.active = self.bbox_layer
        self.bbox_layer.mode = Mode.ADD_BOUNDING_BOX
        
    def remove_bboxes(self, indices):
        if not len(indices):
            return
        # remove the selected_row from napari
        self.bbox_layer.selected_data = indices
        self.bbox_layer.remove_selected()
        self.bbox_layer.refresh()
        
    def update_bbox_z(self, item):
        counter = item.column()
        self.bbox_layer.data[item.row()][counter::2, 0] = float(item.data())
        current_z = self.viewer.dims.point[0]
        self.bbox_layer.data = self.bbox_layer.data
        self.viewer.dims.set_point(0, current_z)
        
    def get_labels_layer_names(self):
        return [x.name for x in self.viewer.layers if isinstance(x, Labels)]
    
    def get_layer(self, layer_name):
        try:
            return self.viewer.layers[layer_name]
        except KeyError:
            return None
        
    def _focus_viewer_on_roi(self, roi_idx):
        center_coords = self.bbox_layer.data_to_world(get_roi_center(self.bbox_layer.data[roi_idx]))
        self.viewer.camera.center = center_coords
        # self._reset_z_viewer(center_coords[0])

    def _reset_z_viewer(self, z: int):
        # reset the z viewer to the z slice of the ROI in world coords
        self.viewer.dims.set_point(0, z)
        
    def _on_mouse_move(self, layer, event):
        yield
        while event.type == "mouse_move":
            yield
        while self.adding_bbox:
            bbox, idx = self.adding_bbox.pop()
            # self.bbox_layer.data = self.bbox_layer.data  # trigger refresh to update dims
            self.bbox_added.emit(bbox, idx)
        self.bbox_selected.emit(list(layer.selected_data))
        
    def _on_update_bbox_layer(self, event):
        """
        Called when the shapes layer is updated by either adding or removing
        ROIs directly in the viewer.
        """
        print('updated')
        if not hasattr(event, 'action'):
            return
        # event with no action attribute is called when the shape has finished drawing (???) 
        # - use this to focus on the ROI after it has been added.        
        if event.action == ActionType.ADDED:
            for r in range(len(self.bbox_layer.data)-1, len(event.value)):
                self.adding_bbox.append((event.value[r], r))
                
        if event.action == ActionType.REMOVED:
            self.bbox_removed.emit(list(event.data_indices))
            