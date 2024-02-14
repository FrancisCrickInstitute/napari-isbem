import napari
from qtpy.QtWidgets import QGridLayout, QGroupBox, QErrorMessage, QLineEdit
from magicgui.widgets import FileEdit
from magicgui.types import FileDialogMode
from tifffile import TiffFile, xml2dict

from napari_sbem_viewer.util import get_ome_pixel_size, display_qt_error


class UploadXrayStack(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 ):
        super().__init__("Upload X-ray stack")
        self.viewer = viewer
        self.setLayout(QGridLayout())
        
        self.filename_edit = FileEdit(
            nullable=True,
            mode=FileDialogMode.EXISTING_FILE)
        self.filename_edit.changed.connect(self._on_upload)
        self.layout().addWidget(self.filename_edit.native, 0, 0, 1, 2)
        
    def _on_upload(self, filename):
        try:
            self._upload_xray_stack(filename)
        except ValueError as e:
            display_qt_error(self, e)
        
    def _upload_xray_stack(self, filename):
        with TiffFile(filename) as tiff:
            tiff = TiffFile(filename)
            xml_metadata = tiff.ome_metadata
            if xml_metadata is None:
                tiff.close()
                raise ValueError("File does not contain OME metadata.")
            metadata = xml2dict(xml_metadata)
            
            try:
                scale = []
                for dim in 'ZYX':
                    scale.append(get_ome_pixel_size(metadata, dim))
                # scale[1], scale[2] = 1, 1  # remove x and y scaling
            except KeyError:
                tiff.close()
                raise ValueError("File does not contain pixel size metadata.")
            
            self.viewer.add_image(tiff.asarray(), name="X-ray stack", scale=scale)
            tiff.close()