from qtpy.QtWidgets import (QGridLayout, 
                            QGroupBox, 
                            QComboBox, 
                            QLabel, 
                            QPushButton, 
                            QMessageBox)


class AddBoundingBoxes(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Add ROI from labels", parent=parent)
        self.setLayout(QGridLayout())
        
        self.layout().addWidget(QLabel("Labels layer"))
        self.combo_box = QComboBox()
        self.layout().addWidget(self.combo_box)
        
        self.upload_button = QPushButton("Add")
        self.layout().addWidget(self.upload_button)
        
    def get_layer_name(self):
        return self.combo_box.currentText()
        
    def update_labels_layers(self, layer_names):
        current_layer_name = self.combo_box.currentText()
        self.combo_box.clear()
        self.combo_box.addItems(layer_names)
        if current_layer_name not in layer_names:
            self.combo_box.setCurrentText(None)
        else:
            self.combo_box.setCurrentText(current_layer_name)
            
    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)
        