import napari
from qtpy.QtWidgets import QVBoxLayout, QWidget, QComboBox, QPushButton, QFileDialog, QMessageBox, QFormLayout, QLabel
from skimage import measure
from napari_tiff import napari_get_reader
from napari.layers import Layer

from napari_sbem_viewer._utils.image_utils import downsample_3d_image_sitk


class AddLabels(QWidget):
    def __init__(self,
                 viewer: napari.Viewer,
                 parent=None
                 ):
        super().__init__(parent=parent)
        self.viewer = viewer
        self.setLayout(QVBoxLayout())
        
        # Downsample factor
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
            self._import_labels(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
                
    def _import_labels(self, file_path):
        reader = napari_get_reader(file_path)
        print(reader(file_path))
        data, metadata_kwargs, _ = reader(file_path)[0]
        del metadata_kwargs['blending']
        del metadata_kwargs['channel_axis']
        del metadata_kwargs['colormap']
        del metadata_kwargs['contrast_limits']
        del metadata_kwargs['rgb']
        
        if data.ndim != 3:
            raise ValueError("Labels must be 3D")
        
        downsample_factor = self._get_downsample_factor()
        if downsample_factor > 1:
            data = downsample_3d_image_sitk(data, downsample_factor)
            if 'scale' in metadata_kwargs:
                metadata_kwargs['scale'] = tuple([s * downsample_factor for s in metadata_kwargs['scale']])
            
        data = measure.label(data)
        self.viewer.add_layer(Layer.create(data, metadata_kwargs, 'labels'))
        
    def _get_downsample_factor(self):
        return 1
        