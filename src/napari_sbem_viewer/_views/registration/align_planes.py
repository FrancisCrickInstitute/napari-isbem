import os

from napari._qt.widgets._slider_compat import QDoubleSlider
from qtpy.QtWidgets import (QPushButton, 
                            QFormLayout, 
                            QFileDialog, 
                            QGridLayout, 
                            QLabel, 
                            QGroupBox,
                            QLabel, 
                            QMessageBox)
from qtpy.QtCore import Qt



class AlignPlanes(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(title='3D rotation', parent=parent)
        self.setMinimumWidth(180)
        self.setLayout(QGridLayout())
        
        self.save_ome_zarr_button = QPushButton("Save as OME-Zarr")
        # self.layout().addWidget(self.save_ome_zarr_button, 1, 1)
        
        self.show_button = QPushButton("Show rotation")
        self.layout().addWidget(self.show_button, 0, 0, 1, 2)
        
        form_layout = QFormLayout()
        self.zy_degrees_slider = QDoubleSlider(Qt.Horizontal)
        self.zy_degrees_slider.setRange(-90, 90)
        self.zy_degrees_slider.setDecimals(1)
        form_layout.addRow(QLabel("Rotate Z-Y"), self.zy_degrees_slider)
        self.zx_degrees_slider = QDoubleSlider(Qt.Horizontal)
        self.zx_degrees_slider.setRange(-90, 90)
        self.zx_degrees_slider.setDecimals(1)
        form_layout.addRow(QLabel("Rotate Z-X"), self.zx_degrees_slider)
        self.position_slider = QDoubleSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 1)
        self.position_slider.setSingleStep(0.01)
        form_layout.addRow(QLabel("Position"), self.position_slider)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.layout().addLayout(form_layout, 1, 0, 1, 2)
        
        self.apply_rotation_button = QPushButton("Apply rotation")
        self.layout().addWidget(self.apply_rotation_button, 2, 0, 1, 2)
        
    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)
        
    def show_info(self, title, message):
        QMessageBox.information(self, title, message)
        
    def open_transform_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 
                                                   "Open File", 
                                                   "", 
                                                   "Text Files (*.txt);;All Files (*)", )
        return file_path
    
    def save_transform_file_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(self, 
                                                   "Save File", 
                                                   "", 
                                                   "Text Files (*.txt);;All Files (*)")
        return file_path        
            
    def save_ome_zarr_file_dialog(self):
        save_path = QFileDialog.getExistingDirectory(self, 
                                                   "Select Save Location", 
                                                   "")
        if not save_path:
            return None
        elif not os.path.exists(save_path):
            QMessageBox.warning(self, "Invalid save location", "Selected folder does not exist.")
            return None
        elif len(os.listdir(save_path)):
            QMessageBox.warning(self, "Invalid save location", "Selected folder is not empty.")
            return None
        elif not save_path.endswith('.ome.zarr'):
            QMessageBox.warning(self, "Invalid save location", "Selected folder must end with '.ome.zarr'.")
            return None
        return save_path
        