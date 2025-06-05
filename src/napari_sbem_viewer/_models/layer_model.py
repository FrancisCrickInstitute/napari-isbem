import tifffile
from napari.layers import Image, Labels, Layer
from napari_ome_zarr import napari_get_reader as zarr_get_reader
from napari_tiff import napari_get_reader as tiff_get_reader
from qtpy.QtCore import QObject, Signal


class LayerModel(QObject):
    """Model for managing napari layers and their events.

    This class handles adding, removing, and exporting targeting, EM, and labels layers
    in a napari viewer. It emits signals when layers are added or removed, and provides
    methods for importing images from OME-Zarr or TIFF files.

    Attributes:
        targeting_layer_added (Signal): Emitted when a targeting layer is added.
        targeting_layer_removed (Signal): Emitted when a targeting layer is removed.
        em_layer_added (Signal): Emitted when an EM layer is added.
        em_layer_removed (Signal): Emitted when an EM layer is removed.
        labels_layer_added (Signal): Emitted when a labels layer is added.
        labels_layer_removed (Signal): Emitted when a labels layer is removed.
        viewer (napari.Viewer): The napari viewer instance.
        targeting_layer (Layer): The current targeting layer.
        targeting_layer_original (Image): Original unrotated targeting image layer.
        em_layer (Layer): The current EM layer.
        labels_layer (Layer): The current labels layer.
        labels_layer_original (Labels): Original unrotated labels layer.
    """

    targeting_layer_added = Signal(object)
    targeting_layer_removed = Signal()
    em_layer_added = Signal(object)
    em_layer_removed = Signal()
    labels_layer_added = Signal(object)
    labels_layer_removed = Signal()

    def __init__(self, viewer):
        """Initializes the LayerModel.

        Args:
            viewer (napari.Viewer): The napari viewer instance.
        """
        super().__init__()
        self.viewer = viewer
        self.targeting_layer = None
        self.targeting_layer_original = None
        self.em_layer = None
        self.labels_layer = None
        self.labels_layer_original = None
        self.viewer.layers.events.removed.connect(self._on_remove_layer)

    def import_targeting_image(self, file_path):
        """Imports a targeting image from an OME-Zarr or TIFF file and adds it as a layer.

        Args:
            file_path (str): Path to the image file (.zarr, .tif, or .tiff).

        Raises:
            ValueError: If the file format is not supported.
        """
        if file_path.endswith('.zarr'):
            reader = zarr_get_reader(file_path)
            layer = Layer.create(*reader(file_path)[0])
        elif file_path.endswith(('.tif', '.tiff')):
            reader = tiff_get_reader(file_path)
            data = reader(file_path)[0]
            del data[1]['colormap']
            del data[1]['channel_axis']
            del data[1]['blending']
            layer = Layer.create(*data)
        else:
            raise ValueError(
                'Invalid file format. Must be an OME-Zarr or TIFF file.'
            )
        self.add_targeting_layer(layer)

    def add_targeting_layer(self, layer):
        """Adds a targeting layer to the viewer and emits a signal.

        Args:
            layer (Image): The targeting layer to add.
        """
        self.targeting_layer = layer
        self.targeting_layer_original = Image(
            layer.data, affine=layer.affine, name=layer.name, scale=layer.scale
        )
        self.viewer.add_layer(layer)
        self.targeting_layer_added.emit(layer)

    def remove_targeting_layer(self):
        """Removes the targeting layer from the viewer and emits a signal."""
        self._remove_layer(self.targeting_layer)
        self.targeting_layer = None
        self.targeting_layer_original = None
        self.targeting_layer_removed.emit()

    def add_em_layer(self, layer):
        """Adds an EM layer to the viewer and emits a signal.

        Args:
            layer (Image): The EM layer to add.
        """
        self.em_layer = layer
        self.viewer.add_layer(layer)
        self.em_layer_added.emit(layer)

    def remove_em_layer(self):
        """Removes the EM layer from the viewer and emits a signal."""
        self._remove_layer(self.em_layer)
        self.em_layer = None
        self.em_layer_removed.emit()

    def add_labels_layer(self, layer):
        """Adds a labels layer to the viewer and emits a signal.

        Args:
            layer (Labels): The labels layer to add.
        """
        self.labels_layer = layer
        self.labels_layer_original = Labels(
            layer.data, affine=layer.affine, name=layer.name, scale=layer.scale
        )
        self.viewer.add_layer(layer)
        self.labels_layer_added.emit(layer)

    def remove_labels_layer(self):
        """Removes the labels layer from the viewer and emits a signal."""
        self._remove_layer(self.labels_layer)
        self.labels_layer = None
        self.labels_layer_original = None
        self.labels_layer_removed.emit()

    def export_labels_layer(self, file_path):
        """Exports the current labels layer to a TIFF file.

        Args:
            file_path (str): Path to save the exported TIFF file.

        Raises:
            ValueError: If there is no labels layer to export.
        """
        if self.labels_layer is None:
            raise ValueError('No labels layer found')
        tifffile.imwrite(file_path, self.labels_layer.data)

    def _remove_layer(self, layer):
        if layer in self.viewer.layers:
            self.viewer.layers.remove(layer)

    def _on_remove_layer(self, event):
        if event.value == self.targeting_layer:
            self.targeting_layer = None
            self.targeting_layer_original = None
            self.targeting_layer_removed.emit()
        elif event.value == self.em_layer:
            self.em_layer = None
            self.em_layer_removed.emit()
        elif event.value == self.labels_layer:
            self.labels_layer = None
            self.labels_layer_original = None
            self.labels_layer_removed.emit()
