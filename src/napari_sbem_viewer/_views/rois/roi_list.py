from qtpy.QtWidgets import (QGroupBox, 
                            QPushButton,
                            QGridLayout, 
                            QTableView, 
                            QHeaderView,
                            QStyledItemDelegate, 
                            QLabel)
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtCore import Qt, QItemSelection, QItemSelectionModel


class ROIList(QGroupBox):
    def __init__(self, parent):
        super().__init__("ROI selection", parent=parent)
        self.setLayout(QGridLayout())
        
        self.current_z_depth_label = QLabel('Current Z: ')
        self.layout().addWidget(self.current_z_depth_label, 0, 0, 1, 2)
        
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        self.layout().addWidget(self.table_view, 1, 0, 1, 2)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['z1 (µm)', 'z2 (µm)'])
        self.table_view.setModel(self.model)
        validation = FloatValidationDelegate()
        self.table_view.setItemDelegateForColumn(0, validation)
        self.table_view.setItemDelegateForColumn(1, validation)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.add_button = QPushButton("Add")
        self.layout().addWidget(self.add_button, 2, 0)
        
        self.remove_button = QPushButton("Remove")
        self.layout().addWidget(self.remove_button, 2, 1)
        
    def clear(self):
        self.model.removeRows(0, self.model.rowCount())

    def get_selected_rows(self):
        indices = self.table_view.selectedIndexes()
        selected_rows = set()
        for idx in indices:
            selected_rows.add(idx.row())
        return list(selected_rows)
    
    def add_roi_to_table(self, coords, row):
        self.table_view.clearSelection()
        z1, z2 = coords.min(axis=0)[0], coords.max(axis=0)[0]
        for c, val in enumerate([f'{z1:.2f}', f'{z2:.2f}']):
            item = QStandardItem(val)
            self.model.setItem(row, c, item)

    def remove_rois_from_table(self, rows):
        # Sort the rows to avoid changing the indices when removing
        for row in sorted(rows, reverse=True):
            self.model.removeRow(row)
                
    def select_rois(self, indices):
        print('selecting rois')
        selection_model = self.table_view.selectionModel()
        selection = QItemSelection()
        selection.clear()
        for idx in indices:
            index_top = self.model.index(idx, 0)
            index_bottom = self.model.index(idx, self.model.columnCount() - 1)
            selection.select(index_top, index_bottom)
        selection_model.select(selection, QItemSelectionModel.Select)
                

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
            