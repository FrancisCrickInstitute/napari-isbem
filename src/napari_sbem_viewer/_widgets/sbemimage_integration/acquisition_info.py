from qtpy.QtWidgets import QGroupBox, QGridLayout, QLabel, QTableView, QHeaderView
from qtpy.QtGui import QStandardItemModel, QStandardItem, QColor
from qtpy.QtCore import Qt

from napari_sbem_viewer._utils.roi_data import ROIState


class AcquisitionInfo(QGroupBox):
    def __init__(self):
        super().__init__("Acquisition info")
        self.setLayout(QGridLayout())
        self.layout().addWidget(QLabel('Current Z-depth:'), 2, 0)
        self.z_depth = QLabel('')
        self.layout().addWidget(self.z_depth, 2, 1)
        self.layout().addWidget(QLabel('Current slice thickness:'), 3, 0)
        self.slice_thickenss = QLabel('')
        self.layout().addWidget(self.slice_thickenss, 3, 1)
        self.layout().addWidget(QLabel('Pause status:'), 4, 0)
        self.pause_status = QLabel('')
        self.layout().addWidget(self.pause_status, 4, 1)
        
        self.table_view = QTableView()
        self.layout().addWidget(self.table_view, 5, 0, 1, 2)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['ROI ID', 'z1', 'z2'])
        self.table_view.setModel(self.model)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    
    def update_acquisition_info(self, z_depth, slice_thickness, pause_status):
        self.z_depth.setText(f'{z_depth:.2f}µm')
        self.slice_thickenss.setText(f'{slice_thickness:.2f}nm')
        self.pause_status.setText('Paused' if pause_status else 'Running')

    def update_roi_info(self, roi_data):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['ROI', 'z1', 'z2'])
        for r, roi in enumerate(roi_data.rois):
            for c, val in enumerate([f'{roi.id}', f'{roi.z1:.2f}µm', f'{roi.z2:.2f}µm']):
                item = QStandardItem(val)
                item.setEditable(False)
                item.setCheckable(False)
                item.setSelectable(False)
                self.model.setItem(r, c, item)
                if roi.state == ROIState.ACQUIRING:
                    self.model.item(r, c).setData(QColor("green"), Qt.TextColorRole)
                    # self.model.item(r, c).setBackground(QColor("green"))
                elif roi.state == ROIState.ACQUIRED:
                    self.model.item(r, c).setData(QColor("grey"), Qt.TextColorRole)
                    # self.model.item(r, c).setBackground(QColor("grey"))