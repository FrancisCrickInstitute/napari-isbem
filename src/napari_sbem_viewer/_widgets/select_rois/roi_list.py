import napari
from napari_bbox import BoundingBoxLayer
from napari_bbox.boundingbox.napari_0_4_18._bounding_box_constants import Mode
from napari.layers.base._base_constants import ActionType
from qtpy.QtWidgets import QGroupBox, QListWidget, QPushButton, QGridLayout, QTableView, QHeaderView, QStyledItemDelegate, QLineEdit
from qtpy.QtGui import QStandardItemModel, QStandardItem, QDoubleValidator
from qtpy.QtCore import Qt, QItemSelection, QItemSelectionModel
import numpy as np
import pandas as pd


class FloatValidationDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.old_value = None

    def setEditorData(self, editor, index):
        # Store old value when editing starts
        self.old_value = index.model().data(index, Qt.EditRole)
        super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        # Get the new value from the editor
        new_value = editor.text()
        try:
            # Try to convert the new value to float
            z = float(new_value)
            
            # Check if z1 is less than z2
            if index.column() == 0:
                z1 = z
                z2 = float(model.item(index.row(), 1).text())
            elif index.column() == 1:
                z1 = float(model.item(index.row(), 0).text())
                z2 = z
            if z1 > z2:
                raise ValueError('z1 must be less than z2')
            
            # If successful, set the new value in the model
            model.setData(index, new_value, Qt.EditRole)
        except ValueError:
            # If conversion fails, revert to the old value
            model.setData(index, self.old_value, Qt.EditRole)


class ROIList(QGroupBox):
    def __init__(self, 
                 viewer: napari.Viewer,
                 parent,
                 bbox_layer_config={}):
        super().__init__("ROI Selection", parent=parent)
        self.viewer = viewer
        self.setLayout(QGridLayout())
        self.bbox_layer_config = bbox_layer_config
        self.adding_row = False
        
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        self.layout().addWidget(self.table_view, 0, 0, 1, 2)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['z1 (µm)', 'z2 (µm)'])
        self.table_view.setModel(self.model)
        selection_model = self.table_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_change_table_selection)
        self.table_view.clicked.connect(self._on_click_roi_table)
        validation = FloatValidationDelegate()
        self.table_view.setItemDelegateForColumn(0, validation)
        self.table_view.setItemDelegateForColumn(1, validation)
        self.model.dataChanged.connect(self._on_change_roi_table)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._on_click_add)
        self.layout().addWidget(self.add_button, 1, 0)
        
        self.remove_button = QPushButton("Remove")
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
        # self._reset_z_viewer(center_coords[0])
        
    def _on_click_add(self):
        if self.bbox_layer is None:
            bounding_box_layer = BoundingBoxLayer(name='ROIs', 
                                                  ndim=3, 
                                                #   features=pd.DataFrame({'name': pd.Series(dtype='str')}),
                                                #   feature_defaults={'name': 'ROI'},
                                                #   text={'string': '{name}'}, 
                                                  **self.bbox_layer_config)
            self.bbox_layer = self.viewer.add_layer(bounding_box_layer)
            self.bbox_layer.events.data.connect(self._on_update_bbox)
            self.bbox_layer.mouse_drag_callbacks.append(self._on_select_bbox)
        self.viewer.layers.selection.active = self.bbox_layer
        self.bbox_layer.mode = Mode.ADD_BOUNDING_BOX
            
    def _on_click_remove(self):
        indices = self._get_selected_rows()
        if not len(indices):
            return
        # remove the selected_row from napari
        self.bbox_layer.selected_data = indices
        self.bbox_layer.remove_selected()
        self.bbox_layer.refresh()
    
    def _get_selected_rows(self):
        indices = self.table_view.selectedIndexes()
        selected_rows = set()
        for idx in indices:
            selected_rows.add(idx.row())
        return list(selected_rows)
        
    def _reset_z_viewer(self, z: int):
        # reset the z viewer to the z slice of the ROI in world coords
        self.viewer.dims.set_point(0, z)
        
    def _on_change_table_selection(self):
        indices = self._get_selected_rows()
        if not len(indices):
            self.bbox_layer.selected_data = []
            self.bbox_layer.refresh()
            return
        
    def _on_click_roi_table(self):
        indices = self._get_selected_rows()
        if not len(indices):
            self.bbox_layer.selected_data = []
            self.bbox_layer.refresh()
            return
        
        # highlight the current point in the viewer
        self.focus_viewer_on_roi(indices[-1])
        self.bbox_layer.selected_data = indices
        self.bbox_layer.refresh()
        
    def _on_change_roi_table(self, item):
        if self.adding_row:
            return
        counter = item.column()
        self.bbox_layer.data[item.row()][counter::2, 0] = float(item.data())
        current_z = self.viewer.dims.point[0]
        self.bbox_layer.data = self.bbox_layer.data
        self.viewer.dims.set_point(0, current_z)

    def _on_update_bbox(self, event):
        """
        Called when the shapes layer is updated by either adding or removing
        ROIs directly in the viewer.
        """
        # event with no action attribute is called when the shape has finished drawing (???) 
        # - use this to focus on the ROI after it has been added.
        if not hasattr(event, 'action'):
            if hasattr(event, 'data_indices'):
                for r in range(self.model.rowCount(), len(event.value)):
                    self._add_roi_to_table(event.value[r], r)
                self.table_view.clearSelection()
                self.viewer.dims.set_point(0, self.current_z)
            return
        
        if event.action == ActionType.ADDING:
            self.current_z = self.viewer.dims.point[0]
            # for idx in event.data_indices:
            #     df = self.bbox_layer.features
            #     self.bbox_layer.features.loc[idx, "name"] = f'ROI {idx+1}'
        
        if event.action == ActionType.REMOVING:
            self.curent_z = self.viewer.dims.point[0]
        
        # if event.action == ActionType.ADDED:
        #     for r in range(self.model.rowCount(), len(event.value)):
        #         self._add_roi_to_table(event.value[r], r)
        #     self.table_view.selectRow(-1)
    
        if event.action == ActionType.REMOVED:
            self._remove_rois_from_table(event.data_indices)
            # self.viewer.dims.set_point(0, self.current_z)
                
    def _on_select_bbox(self, layer, event):
        yield
        while event.type == "mouse_move":
            yield
        for idx in layer.selected_data:
            self.table_view.selectRow(idx)
        selection_model = self.table_view.selectionModel()
        selection = QItemSelection()
        selection.clear()
        for idx in layer.selected_data:
            index_top = self.model.index(idx, 0)
            index_bottom = self.model.index(idx, self.model.columnCount() - 1)
            selection.select(index_top, index_bottom)
        selection_model.select(selection, QItemSelectionModel.Select)
                
    def _add_roi_to_table(self, coords, row):
        self.adding_row = True
        z1, z2 = coords.min(axis=0)[0], coords.max(axis=0)[0]
        for c, val in enumerate([f'{z1:.2f}', f'{z2:.2f}']):
            item = QStandardItem(val)
            self.model.setItem(row, c, item)
        self.adding_row = False

    def _remove_rois_from_table(self, rows):
        # Sort the rows to avoid changing the indices when removing
        for row in sorted(rows, reverse=True):
            self.model.removeRow(row)
        
def get_roi_center(coords_list):
    # calculate the min / max values of the x, y and z coordinates
    min_coords = np.min(coords_list, axis=0)
    max_coords = np.max(coords_list, axis=0)
    center_coords = (min_coords + max_coords) / 2
    return center_coords
