from napari.layers import Image
from napari.layers.base._base_constants import ActionType, Mode
from qtpy.QtCore import QObject, Signal

from napari_sbem_viewer._utils.general_utils import reset_view
from napari_sbem_viewer._utils.registration_utils import (
    calculate_transform,
    calculate_z_transform,
    convert_affine_to_ndims,
    flip_transform_matrix,
    is_2d_affine_matrix,
    offset_transform_matrix_z,
    Align2DMethods,
)


class AffineModel(QObject):    
    """Model for managing affine registration between two image layers in napari.

    This class handles the logic for interactive affine registration, including
    managing points layers, and computing and applying transformation matrices.
    This handles the z-translation and flipping of the targeting images as well
    as the 2D affine transformation based on user-defined points.

    Attributes:
        activated (Signal): Emitted when the necessary layers for registration are added (e.g. both the EM and targeting layers).
        deactivated (Signal): Emitted when either the EM or targeting layers are removed.
        transform_loaded (Signal): Emitted when a transformation matrix is loaded or reset.
        viewer: The napari viewer instance.
        layer_model: The model managing image layers for registration.
        delete_pts (bool): Whether to delete points after ending the registration.
        points_layers (list): List containing the fixed and moving points layers.
        is_doing_registration (bool): Whether registration is currently active.
        transform_method (Align2DMethods): The transformation method used for registration.
        remove_outliers (bool): Whether to remove outliers during transformation.
    """
    activated = Signal()
    deactivated = Signal()
    transform_loaded = Signal()

    def __init__(self, viewer, layer_model):
        super().__init__()
        self.viewer = viewer
        self.layer_model = layer_model
        self.delete_pts = True
        self.points_layers = [None, None]
        self.is_doing_registration = False
        self.transform_method = Align2DMethods.Euclidean
        self.remove_outliers = False
        self.layer_model.targeting_layer_added.connect(self._on_add_layer)
        self.layer_model.targeting_layer_removed.connect(self._on_remove_layer)
        self.layer_model.em_layer_added.connect(self._on_add_layer)
        self.layer_model.em_layer_removed.connect(self._on_remove_layer)

    def start_registration(self):
        """Begins the interactive registration process.

        Raises:
            ValueError: If required image layers are not selected or are invalid.
        """
        if (
            not self.layer_model.targeting_layer
            or not self.layer_model.em_layer
        ):
            raise ValueError('No images selected')

        if not isinstance(
            self.layer_model.targeting_layer, Image
        ) or not isinstance(self.layer_model.em_layer, Image):
            raise ValueError('Both layers must be images')

        if self.layer_model.targeting_layer == self.layer_model.em_layer:
            raise ValueError('Images must be different')

        self.layer_model.targeting_layer.events.affine.connect(
            self._affine_callback
        )
        self._create_points_layers()

        pts_layer0 = self.points_layers[0]
        pts_layer1 = self.points_layers[1]
        pts_layer0.events.data.connect(self._on_add_point)
        pts_layer1.events.data.connect(self._on_add_point)

        # get the layer order started
        for layer in [
            self.layer_model.em_layer,
            pts_layer0,
            self.layer_model.targeting_layer,
            pts_layer1,
        ]:
            self.viewer.layers.move(self.viewer.layers.index(layer), -1)

        self._focus_fixed_layer()
        self.is_doing_registration = True

    def stop_registration(self):
        """Stops the registration process and cleans up points layers."""
        if not self.is_doing_registration:
            return
        self.layer_model.targeting_layer.mode = Mode.PAN_ZOOM
        self.layer_model.targeting_layer.events.affine.disconnect(
            self._affine_callback
        )
        self._remove_points_layers()
        self.is_doing_registration = False

    def reset_transform(self):
        """Stops registration and emits a signal to indicate the transform was reset."""
        self.stop_registration()
        self.transform_loaded.emit()

    def load_transform(self, affine_matrix):
        """Loads and applies a 2D affine transform to the moving image layer.

        Args:
            affine_matrix (np.ndarray): The 2D affine matrix to apply.

        Raises:
            ValueError: If the provided matrix is not a valid 2D affine matrix.
        """
        if not is_2d_affine_matrix(affine_matrix):
            print(affine_matrix)
            raise ValueError(
                'Invalid transform matrix. Must be a 2D affine matrix.'
            )
        self.layer_model.targeting_layer.affine = convert_affine_to_ndims(
            affine_matrix, self.layer_model.targeting_layer.ndim
        )
        self.transform_loaded.emit()

    def get_affine_matrix(self):
        """Returns the current affine matrix of the moving image layer.

        Returns:
            np.ndarray: The affine matrix.

        Raises:
            ValueError: If no moving image layer is selected.
        """
        if self.layer_model.targeting_layer is None:
            raise ValueError('No moving image layer selected')
        return self.layer_model.targeting_layer.affine.affine_matrix

    def is_z_flipped(self):
        """Checks if the Z axis of the moving image layer is flipped.

        Returns:
            bool: True if Z is flipped, False otherwise.
        """
        if not self.layer_model.targeting_layer:
            return False
        return self.layer_model.targeting_layer.affine.affine_matrix[0, 0] < 0
    
    def set_transform_method(self, method):
        """Sets the transformation method for registration.

        Args:
            method (str): The name of the transformation method.

        Raises:
            ValueError: If the method name is invalid.
        """
        try:
            self.transform_method = Align2DMethods[method]
        except KeyError:
            raise ValueError(f'Invalid transform method: {method}')

    def do_transform(self):
        """Calculates and applies the affine transform based on point correspondences."""
        fixed_points_layer, moving_points_layer = self.points_layers
        if (
            self.layer_model.em_layer is None
            or self.layer_model.targeting_layer is None
        ):
            return
        if fixed_points_layer is None or moving_points_layer is None:
            return
        pts0, pts1 = fixed_points_layer.data, moving_points_layer.data
        ndim_raw = pts0.shape[1]  # shape of raw points
        pts0, pts1 = pts0[:, -2:], pts1[:, -2:]
        ndim = pts0.shape[1]  # shape of points after potentially changing to 2D
        if len(pts0) != len(pts1) or len(pts0) <= ndim:
            return
        mat = calculate_transform(
            pts0,
            pts1,
            transform_method=self.transform_method,
            remove_outliers=self.remove_outliers,
        )
        # if image is 3D, add z-shift to 2D transform
        if ndim_raw > 2:
            z_mat = calculate_z_transform(
                fixed_points_layer, moving_points_layer, self.is_z_flipped()
            )
            mat = z_mat @ convert_affine_to_ndims(mat, ndim_raw)
        ref_mat = self.layer_model.em_layer.affine.affine_matrix
        # must shrink ndims of affine matrix if dims of image layer is bigger than moving layer
        if (
            self.layer_model.em_layer.ndim
            > self.layer_model.targeting_layer.ndim
        ):
            ref_mat = convert_affine_to_ndims(
                ref_mat, self.layer_model.targeting_layer.ndim
            )
        # must pad affine matrix with identity matrix if dims of moving layer smaller
        self.layer_model.targeting_layer.affine = convert_affine_to_ndims(
            (ref_mat @ mat), self.layer_model.targeting_layer.ndim
        )
        moving_points_layer.affine = convert_affine_to_ndims(
            (ref_mat @ mat), moving_points_layer.ndim
        )

    def flip_z(self):
        """Flips the Z axis of the moving image and its points layer."""
        moving_points_layer = self.points_layers[1]
        if self.layer_model.targeting_layer is not None:
            mat = convert_affine_to_ndims(
                self.layer_model.targeting_layer.affine.affine_matrix, 3
            )
            mat = flip_transform_matrix(
                mat,
                self.layer_model.targeting_layer.data.shape[-3]
                * self.layer_model.targeting_layer.scale[-3],
            )
            self.layer_model.targeting_layer.affine = convert_affine_to_ndims(
                mat, self.layer_model.targeting_layer.ndim
            )
            if moving_points_layer is not None:
                moving_points_layer.affine = convert_affine_to_ndims(
                    mat, moving_points_layer.ndim
                )

    def offset_z(self, offset):
        """Offsets the Z position of the moving image and its points layer.

        Args:
            offset (float): The amount to offset in Z (in microns).
        """
        moving_points_layer = self.points_layers[1]
        if self.layer_model.targeting_layer is not None:
            current_z = self.viewer.dims.point[0]
            mat = convert_affine_to_ndims(
                self.layer_model.targeting_layer.affine.affine_matrix, 3
            )
            offset_transform_matrix_z(mat, offset)
            self.layer_model.targeting_layer.affine = convert_affine_to_ndims(
                mat, self.layer_model.targeting_layer.ndim
            )
            if moving_points_layer is not None:
                moving_points_layer.affine = convert_affine_to_ndims(
                    mat, moving_points_layer.ndim
                )
            self.viewer.dims.set_point(0, current_z)
            
    def _on_add_layer(self, layer):
        if (
            self.layer_model.em_layer is not None
            and self.layer_model.targeting_layer is not None
        ):
            self.activated.emit()

    def _on_remove_layer(self):
        self.deactivated.emit()

    def _create_points_layers(self):
        # set points layer for each image
        # Use C0 and C1 from matplotlib color cycle
        points_layers_to_add = [
            (self.layer_model.em_layer, (0.122, 0.467, 0.706, 1.0)),
            (self.layer_model.targeting_layer, (1.0, 0.498, 0.055, 1.0)),
        ]

        # make points layer if it was not specified
        estimation_ndim = min(
            self.layer_model.em_layer.ndim,
            self.layer_model.targeting_layer.ndim,
        )
        for i in range(len(self.points_layers)):
            if self.points_layers[i] not in self.viewer.layers:
                layer, color = points_layers_to_add[i]
                new_layer = self.viewer.add_points(
                    ndim=estimation_ndim,  # ndims of all points layers same lowest ndim of fixed or moving
                    name=layer.name + '_pts',
                    affine=convert_affine_to_ndims(
                        layer.affine, estimation_ndim
                    ),
                    face_color=[color],
                )
                self.points_layers[i] = new_layer

    def _focus_fixed_layer(self, reset_camera=True):
        fixed_points_layer = self.points_layers[0]
        self.viewer.layers.selection.active = fixed_points_layer
        self.viewer.layers.move(
            self.viewer.layers.index(self.layer_model.em_layer), -1
        )
        self.viewer.layers.move(
            self.viewer.layers.index(fixed_points_layer), -1
        )
        fixed_points_layer.mode = 'add'
        if reset_camera:
            reset_view(self.viewer, self.layer_model.em_layer)
        if len(fixed_points_layer.data):
            z_height = fixed_points_layer.data[-1][0]
            self.viewer.dims._increment_dims_right(
                0
            )  # TODO: instead of incrementing, find a way to refresh the viewer without changing the dims
            self.viewer.dims.set_point(0, z_height)

    def _focus_moving_layer(self, reset_camera=True):
        moving_points_layer = self.points_layers[1]
        self.viewer.layers.selection.active = moving_points_layer
        self.viewer.layers.move(
            self.viewer.layers.index(self.layer_model.targeting_layer), -1
        )
        self.viewer.layers.move(
            self.viewer.layers.index(moving_points_layer), -1
        )
        moving_points_layer.mode = 'add'
        if reset_camera:
            reset_view(self.viewer, self.layer_model.targeting_layer)

    def _remove_points_layers(self):
        for layer in self.points_layers:
            if layer in self.viewer.layers:
                self.viewer.layers.remove(layer)
        self.points_layers = [None, None]

    def _affine_callback(self):
        moving_points_layer = self.points_layers[1]
        moving_points_layer.affine = convert_affine_to_ndims(
            self.layer_model.targeting_layer.affine.affine_matrix,
            moving_points_layer.ndim,
        )

    def _on_add_point(self, event):
        if not event.action == ActionType.ADDED:
            return
        fixed_points_layer, moving_points_layer = self.points_layers
        reset_camera = (
            len(fixed_points_layer.data) < fixed_points_layer.ndim + 1
        )
        if fixed_points_layer in self.viewer.layers.selection:
            self._focus_moving_layer(reset_camera=reset_camera)
        elif moving_points_layer in self.viewer.layers.selection:
            self.do_transform()
            self._focus_fixed_layer(reset_camera=reset_camera)
