from qtpy.QtWidgets import (QGridLayout, 
                            QPushButton, 
                            QFileDialog, 
                            QDoubleSpinBox,
                            QComboBox, 
                            QLabel, 
                            QCheckBox, 
                            QGroupBox, 
                            QMessageBox)


class ManualRegistration(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(title='2D affine transform', parent=parent)
        
        self.setLayout(QGridLayout())
        
        # ----------------- Z adjustment -----------------
        self.reverse_checkbox = QCheckBox("Reverse Z direction")
        self.layout().addWidget(self.reverse_checkbox, 0, 0, 1, 2)
        
        self.move_amount_slider = QDoubleSpinBox(
            minimum=0.1, maximum=10, singleStep=0.1, value=1)
        self.layout().addWidget(QLabel("Move amount (µm):"), 1, 0)
        self.layout().addWidget(self.move_amount_slider, 1, 1)
        self.move_down_button = QPushButton("Move down")
        self.move_down_button.setAutoRepeat(True)
        self.layout().addWidget(self.move_down_button, 2, 0)
        self.move_up_button = QPushButton("Move up")
        self.move_up_button.setAutoRepeat(True)
        self.layout().addWidget(self.move_up_button, 2, 1)
        
        # ----------------- 2D transform -----------------
        self.model_combobox = QComboBox()
        self.model_label = QLabel("Model:")
        # model_layout = QHBoxLayout()
        # model_layout.addWidget(self.model_label)
        # model_layout.addWidget(self.model_combobox)
        # model_layout.setStretch(1, 1)
        # self.layout().addLayout(model_layout, 4, 0, 1, 2)
        
        self.remove_outliers_checkbox = QCheckBox("Remove outliers")
        self.layout().addWidget(self.remove_outliers_checkbox, 3, 0, 1, 2)
        
        self.start_button = QPushButton("Start")
        self.layout().addWidget(self.start_button, 4, 0)
    
        self.stop_button = QPushButton("Stop")
        self.layout().addWidget(self.stop_button, 4, 1)
        
        self.reset_button = QPushButton("Reset transform")
        self.layout().addWidget(self.reset_button, 5, 0, 1, 2)
        
        self.layout().setRowStretch(self.layout().rowCount(), 1)
    
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 
                                                   "Open File", 
                                                   "", 
                                                   "Text Files (*.txt);;All Files (*)")
        return file_path
    
    def save_file_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(self, 
                                                   "Save File", 
                                                   "", 
                                                   "Text Files (*.txt);;All Files (*)")
        return file_path     
    
    def reset_confirmation_dialog(self):
        reply = QMessageBox.question(self, 'Confirmation',
                                     'Are you sure you want to reset the transformation?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes
    
    def show_error(self, e):
        QMessageBox.critical(self, "Error", f"{e}")
        