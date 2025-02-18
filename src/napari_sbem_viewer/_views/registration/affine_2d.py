from qtpy.QtWidgets import (QGridLayout, 
                            QPushButton, 
                            QCheckBox, 
                            QGroupBox, 
                            QMessageBox)


class Affine2d(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(title='2D affine transform', parent=parent)
        
        self.setLayout(QGridLayout())
        
        # ----------------- 2D transform -----------------
        self.remove_outliers_checkbox = QCheckBox("Remove outliers")
        self.layout().addWidget(self.remove_outliers_checkbox, 0, 0, 1, 2)
        
        self.start_button = QPushButton("Start")
        self.layout().addWidget(self.start_button, 1, 0)
    
        self.stop_button = QPushButton("Stop")
        self.layout().addWidget(self.stop_button, 1, 1)
        
        self.reset_button = QPushButton("Reset transform")
        self.layout().addWidget(self.reset_button, 2, 0, 1, 2)
        
        self.layout().setRowStretch(self.layout().rowCount(), 1)
    
    def reset_confirmation_dialog(self):
        reply = QMessageBox.question(self, 'Confirmation',
                                     'Are you sure you want to reset the transformation?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes
    
    def show_error(self, e):
        QMessageBox.critical(self, "Error", f"{e}")
        