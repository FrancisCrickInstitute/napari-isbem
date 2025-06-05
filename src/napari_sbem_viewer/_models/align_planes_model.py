import numpy as np
from napari.layers import Image
from napari.qt import create_worker
from qtpy.QtCore import QObject, Signal

from napari_sbem_viewer._utils.registration_utils import (
    calculate_normal,
    is_rotation_matrix,
    rotation_matrix_from_zy_zx_angles,
    transform_layer,
)


class AlignPlanesModel(QObject):
    """Model for aligning planes in 3D image data using rotation and affine transforms.

    This class manages the logic for interactively rotating a 3D image layer in a separate
    napari viewer window. It provides methods for applying rotations to the image and label
    layers. It also handles saving and loading rotation transform matrices.

    Attributes:
        rotation_started: Signal emitted when rotation starts in an alternate thread.
        rotation_finished: Signal emitted when rotation finishes successfully.
        rotation_errored: Signal emitted when an error occurs during rotation.
        viewer: The main napari viewer instance.
        align_planes_window: The window or viewer used for plane alignment.
        layer_model: The model managing image and label layers.
        shape: Shape of the downsampled image data.
        t: Current interpolation parameter for plane position.
        intersection_points: List of two points defining the plane intersection range.
        affine_matrix: The current affine (rotation) matrix applied.
    """

    rotation_started = Signal()
    rotation_finished = Signal(object)
    rotation_errored = Signal(Exception)

    def __init__(self, viewer, stack_viewer, layer_model):
        """Initializes the AlignPlanesModel.

        Args:
            viewer: The main napari viewer instance.
            stack_viewer: The StackViewer instance for viewing plane alignment.
            layer_model: The LayerModel instance for managing image and label layers.
        """
        super().__init__()
        self.viewer = viewer
        self.align_planes_window = stack_viewer
        self.layer_model = layer_model
        self.layer_model.targeting_layer_added.connect(
            self._on_add_targeting_layer
        )
        self.layer_model.targeting_layer_removed.connect(self.reset)
        self.layer_model.labels_layer_added.connect(self._on_add_labels_layer)
        self.align_planes_window.image_layer = None
        self.align_planes_window.plane_layer = None
        self.shape = None
        self.t = None
        self.intersection_points = None
        self.affine_matrix = None

    def apply_rotation(self, zy_degrees, zx_degrees):
        """Applies a rotation to the targeting layer using the given angles.

        Args:
            zy_degrees (float): Rotation angle around the ZY axis in degrees.
            zx_degrees (float): Rotation angle around the ZX axis in degrees.
        """
        transform_matrix = rotation_matrix_from_zy_zx_angles(
            zy_degrees, zx_degrees
        )
        self.apply_transform(transform_matrix)

    def apply_transform(self, transform_matrix):
        """Applies a given transformation matrix to the targeting and label layers.

        Args:
            transform_matrix (np.ndarray): The affine transformation matrix to apply.
        """
        self.rotation_started.emit()
        create_worker(
            self._rotate_images,
            transform_matrix,
            _connect={
                'returned': lambda res: self._on_finish_apply_rotation(*res),
                'errored': self.rotation_errored.emit,
            },
        )
        self.affine_matrix = transform_matrix

    def load_transform(self, affine_matrix):
        """Loads and applies a rotation matrix to the targeting layer and image layer if it exists.

        Args:
            affine_matrix (np.ndarray): The rotation matrix to apply.

        Raises:
            ValueError: If the matrix is not a valid rotation matrix.
        """
        if not is_rotation_matrix(affine_matrix):
            print(affine_matrix)
            raise ValueError(
                'Invalid transform matrix. Must be a rotation matrix.'
            )
        self.apply_transform(affine_matrix)

    def get_rotation_matrix(self):
        """Returns the current affine (rotation) matrix.

        Returns:
            np.ndarray: The current affine matrix.
        """
        return self.affine_matrix

    def show_align_planes_window(self):
        """Displays the align planes window with the current targeting image."""
        moving_layer = self.layer_model.targeting_layer
        if not isinstance(moving_layer, Image):
            raise ValueError('Can only show image layers.')

        self.layer_model.targeting_layer_original.contrast_limits = (
            self.layer_model.targeting_layer.contrast_limits
        )
        self.align_planes_window.viewer.layers.clear()

        im_data = self.layer_model.targeting_layer_original.data
        im_data_downsample = get_downsampled_data(
            im_data,
            multiscale=self.layer_model.targeting_layer_original.multiscale,
        )
        self.align_planes_window.image_layer = Image(
            data=im_data_downsample,
            name='image',
            scale=self.layer_model.targeting_layer_original.scale,
            contrast_limits=self.layer_model.targeting_layer.contrast_limits,
            blending='translucent',
            colormap='gray',
        )
        self.align_planes_window.plane_layer = Image(
            data=im_data_downsample,
            name='plane',
            scale=self.layer_model.targeting_layer_original.scale,
            contrast_limits=self.layer_model.targeting_layer.contrast_limits,
            blending='translucent_no_depth',
            colormap='cyan',
            depiction='plane',
        )

        self.shape = im_data_downsample.shape
        self.align_planes_window.plane_layer.plane.position = (
            np.array(self.shape) / 2
        )
        self._calculate_intersection_points()

        self.align_planes_window.viewer.add_layer(
            self.align_planes_window.image_layer
        )
        self.align_planes_window.viewer.add_layer(
            self.align_planes_window.plane_layer
        )
        self.align_planes_window.show()

    def reset(self):
        """Resets the alignment state and closes the align planes window."""
        self.align_planes_window.image_layer = None
        self.align_planes_window.plane_layer = None
        self.layer = None
        self.shape = None
        self.t = None
        self.affine_matrix = None
        self.intersection_points = None
        self.align_planes_window.close()
        self.align_planes_window.viewer.layers.clear()
        self.rotation_finished.emit(self.affine_matrix)

    def reset_transform(self):
        """Resets the targeting and label layers to their original unrotated state."""
        self.affine_matrix = None
        self.layer_model.targeting_layer.data = (
            self.layer_model.targeting_layer_original.data
        )
        self.layer_model.targeting_layer.affine = (
            self.layer_model.targeting_layer_original.affine
        )
        self.layer_model.targeting_layer.translate = (
            self.layer_model.targeting_layer_original.translate
        )
        self.layer_model.targeting_layer.scale = (
            self.layer_model.targeting_layer_original.scale
        )
        if self.layer_model.labels_layer is not None:
            self.layer_model.labels_layer.data = (
                self.layer_model.labels_layer_original.data
            )
            self.layer_model.labels_layer.affine = (
                self.layer_model.targeting_layer_original.affine
            )
            self.layer_model.labels_layer.translate = (
                self.layer_model.targeting_layer_original.translate
            )
            self.layer_model.labels_layer.scale = (
                self.layer_model.targeting_layer_original.scale
            )
        self.rotation_finished.emit(self.affine_matrix)

    def update_plane_angle(self, zy_degrees, zx_degrees):
        """Updates the orientation of the plane layer based on the given angles.

        Args:
            zy_degrees (float): Rotation angle around the ZY axis in degrees.
            zx_degrees (float): Rotation angle around the ZX axis in degrees.
        """
        if self.align_planes_window.plane_layer is None:
            return

        normal = calculate_normal(zy_degrees, zx_degrees)
        self.align_planes_window.plane_layer.plane.normal = normal
        self._calculate_intersection_points()
        self._calculate_current_position()

    def _rotate_images(self, transform_matrix):
        """Rotates the targeting layer and the labels layer if it exists using the given matrix.

        Args:
            transform_matrix (np.ndarray): The affine transformation matrix.

        Returns:
            tuple: Transformed image and label layers.
        """
        image = transform_layer(
            self.layer_model.targeting_layer_original, transform_matrix
        )
        labels = None
        if (
            self.layer_model.labels_layer is not None
            and self.layer_model.labels_layer_original is not None
        ):
            labels = transform_layer(
                self.layer_model.labels_layer_original, transform_matrix
            )
        return image, labels

    def _on_finish_apply_rotation(self, image_layer, labels_layer):
        """Updates the viewer and layers after rotation is finished.

        Args:
            image_layer: The rotated image layer.
            labels_layer: The rotated labels layer, or None.
        """
        self.layer_model.targeting_layer.data = image_layer.data
        self.layer_model.targeting_layer.translate = image_layer.translate
        self.layer_model.targeting_layer.scale = image_layer.scale
        if (
            self.layer_model.labels_layer is not None
            and labels_layer is not None
        ):
            self.layer_model.labels_layer.data = labels_layer.data
            self.layer_model.labels_layer.scale = labels_layer.scale
            self.layer_model.labels_layer.affine = (
                self.layer_model.targeting_layer.affine
            )
            self.layer_model.labels_layer.translate = (
                self.layer_model.targeting_layer.translate
            )
        self.rotation_finished.emit(self.affine_matrix)

    def _on_add_targeting_layer(self, layer):
        self.reset()
        self.layer_model.targeting_layer.events.affine.connect(
            self._on_affine_changed
        )

    def _on_add_labels_layer(self, labels_layer):
        self.layer_model.labels_layer.events.data.connect(
            self._on_labels_data_changed
        )
        if self.affine_matrix is not None:
            new_layer = transform_layer(
                self.layer_model.labels_layer_original, self.affine_matrix
            )
            self.layer_model.labels_layer.data = new_layer.data
            self.layer_model.labels_layer.scale = new_layer.scale
        if self.layer_model.targeting_layer is not None:
            self.layer_model.labels_layer.affine = (
                self.layer_model.targeting_layer.affine
            )
            self.layer_model.labels_layer.translate = (
                self.layer_model.targeting_layer.translate
            )

    def _calculate_intersection_points(self):
        # contruct 3D points for corners of image
        points = np.array(
            [
                [0, 0, 0],
                [0, 0, self.shape[2]],
                [0, self.shape[1], 0],
                [0, self.shape[1], self.shape[2]],
                [self.shape[0], 0, 0],
                [self.shape[0], 0, self.shape[2]],
                [self.shape[0], self.shape[1], 0],
                [self.shape[0], self.shape[1], self.shape[2]],
            ]
        )
        position = self.align_planes_window.plane_layer.plane.position
        normal = self.align_planes_window.plane_layer.plane.normal

        # calculate min distances from the plane to each corner
        distances = np.dot(points - position, normal)

        # find the corners that are closest and farthest from the plane
        max_dist = np.max(distances)
        min_dist = np.min(distances)
        min_corners = points[np.where(distances == max_dist)]
        max_corners = points[np.where(distances == min_dist)]

        # if there are multiple corners with the same distance, take the average.
        # position slider moves plane between intersection points
        self.intersection_points = [
            np.mean(min_corners, axis=0),
            np.mean(max_corners, axis=0),
        ]

    def _calculate_current_position(self):
        num = -np.dot(
            self.align_planes_window.plane_layer.plane.normal,
            self.intersection_points[0]
            - self.align_planes_window.plane_layer.plane.position,
        )
        denom = np.dot(
            self.align_planes_window.plane_layer.plane.normal,
            self.intersection_points[1] - self.intersection_points[0],
        )
        t = num / denom
        self.t = t

    def update_plane_position(self, t):
        """Updates the position of the plane layer based on the interpolation parameter.

        Args:
            t (float): Interpolation parameter between the two intersection points (0 to 1).
        """
        if self.align_planes_window.plane_layer is None:
            return
        new_position = (1 - t) * self.intersection_points[
            0
        ] + t * self.intersection_points[1]
        self.align_planes_window.plane_layer.plane.position = new_position
        self.t = t

    def _on_labels_data_changed(self):
        if self.layer_model.labels_layer and self.affine_matrix is None:
            self.layer_model.labels_layer_original.data = (
                self.layer_model.labels_layer.data
            )

    def _on_affine_changed(self):
        if self.layer_model.labels_layer:
            self.layer_model.labels_layer.affine = (
                self.layer_model.targeting_layer.affine
            )


def find_min_max_corners(normal, p, points):
    distances = np.dot(points - p, normal)
    return distances.min(), distances.max()


def get_downsampled_data(data, multiscale=False):
    if multiscale:
        # TODO: choose layer based on image shapes
        if len(data) > 1:
            # return the second pyramid level if it exists
            return data[1].compute()
        else:
            # return the first pyramid level
            return data[0].compute()

    else:
        return data  # TODO: downsample and cache if image is too large
