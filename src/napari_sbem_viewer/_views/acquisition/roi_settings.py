from qtpy.QtGui import QStandardItemModel, QStandardItem, QColor
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QTableView,
                            QLabel, 
                            QHeaderView,
                            QGroupBox, 
                            QVBoxLayout, 
                            QHBoxLayout,
                            QComboBox, 
                            QMessageBox)

from napari_sbem_viewer._models import ROIState


DEFAULT_FINE_THICKNESS = 50


class ROISettings(QGroupBox):
    def __init__(self):
        super().__init__("ROI settings")
        self.setLayout(QVBoxLayout())
        
        self.roi_combo_box = QComboBox()
        roi_lyt = QHBoxLayout()
        roi_lyt.addWidget(QLabel("ROI layer"))
        # add stretch to the combo box
        roi_lyt.addWidget(self.roi_combo_box, 1)
        self.layout().addLayout(roi_lyt)
        
        self.table_view = QTableView()
        self.layout().addWidget(self.table_view)
        self.model = QStandardItemModel()
        
        self.table_view.setModel(self.model)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
    def update_roi_info(self, roi_data):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['ROI ID', 'z1 (µm)', 'z2 (µm)'])
        for r, roi in enumerate(roi_data.rois):
            for c, val in enumerate([f'{roi.id}', f'{roi.z1:.2f}', f'{roi.z2:.2f}']):
                item = QStandardItem(val)
                item.setEditable(False)
                item.setCheckable(False)
                item.setSelectable(False)
                self.model.setItem(r, c, item)
                if roi.state == ROIState.ACQUIRING:
                    self.model.item(r, c).setData(QColor("green"), Qt.TextColorRole)
                elif roi.state == ROIState.ACQUIRED:
                    self.model.item(r, c).setData(QColor("grey"), Qt.TextColorRole)
                    
    def reset(self):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['ROI ID', 'z1 (µm)', 'z2 (µm)'])
        self.roi_combo_box.setCurrentIndex(0)
    
    def show_error(self, title, text):
        QMessageBox.warning(self, title, text)
        