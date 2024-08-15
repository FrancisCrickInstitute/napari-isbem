import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QComboBox, QPushButton, QFileDialog, QMessageBox, QFormLayout, QLabel
from skimage import measure
from napari_tiff import napari_get_reader
from napari.layers import Layer

from napari_sbem_viewer._utils.image_utils import downsample_3d_image_sitk
from napari_sbem_viewer._reader import get_labels_reader


class AddLabels(QWidget):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__(parent=parent)
        self.viewer = viewer
        self.setLayout(QVBoxLayout())
        
        form_layout = QFormLayout()
        self.downsample_combo_box = QComboBox()
        self.downsample_combo_box.addItems(['1x', '2x', '4x', '8x'])
        form_layout.addRow(QLabel("Downsample"), self.downsample_combo_box)
        # self.layout().addLayout(form_layout)

        self.import_button = QPushButton("Import Labels")
        self.import_button.clicked.connect(self._on_click_import)
        self.layout().addWidget(self.import_button)

    def _on_click_import(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, 
                                                   "Save File", 
                                                   "", 
                                                   "Tiff Files (*.tif *.tiff);;All Files (*)", 
                                                   options=options)
        if not file_path:
            return     
        try:
            reader = get_labels_reader(file_path)
            if reader is None:
                raise ValueError("Unsupported file format")
            self.viewer.add_layer(Layer.create(*reader(file_path)[0]))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        