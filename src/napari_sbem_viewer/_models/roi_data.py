from enum import Enum

import numpy as np

from napari_sbem_viewer._utils.image_utils import get_bounds_from_labels
from napari_sbem_viewer._utils.registration_utils import (
    add_scale_to_transform_matrix,
    add_translation_to_transform_matrix,
    find_bounds,
    transform_image_3d_sitk,
)


class ROIState(Enum):
    ACQUIRING = 1
    ACQUIRED = 2
    REMAINING = 3


class ROIData:
    """Class for managing Regions of Interest (ROIs) and their states.

    This class handles the creation and removal of ROIs stored as `MaskROI` objects.
    ROIs can be added from a labels layer, and their imaging state can be updated
    based on the current z-depth of the acquisition.

    Attributes:
        rois (list): List of MaskROI objects.
        acquiring_rois (set): Set of ROIs currently being acquired.
        remaining_rois (set): Set of ROIs remaining to be acquired.
        _offset (np.ndarray): Offset for coordinate transformations.
    """

    def __init__(self):
        """Initializes the ROIData object."""
        self.rois = []
        self.acquiring_rois = set()
        self.remaining_rois = set()
        self._offset = np.asarray([0, 0, 0])

    def add_masks(self, labels_layer, combine_masks=False):
        """Adds ROIs from a labels layer, extracting masks and transforming coordinates.

        Args:
            labels_layer: The napari labels layer containing ROI masks.
            combine_masks (bool, optional): If True, combine all masks into one. Defaults to False.
        """
        labels = labels_layer.data
        if combine_masks:
            labels[labels > 0] = 1
        bounds, label_ids = get_bounds_from_labels(labels.astype(np.uint8))
        for (mins, maxes), label_id in zip(bounds, label_ids):
            # Add the scale and translation to the affine transform matrix
            T = add_scale_to_transform_matrix(
                labels_layer.affine.affine_matrix, labels_layer.scale
            )
            T = add_translation_to_transform_matrix(T, labels_layer.translate)

            # Find the boundaries of the transformed ROI
            size = (maxes - mins).astype(np.float32)
            offset = mins.astype(np.float32) - 0.5
            mins_t, maxes_t = find_bounds(size, T, offset)

            # Obtain the mask for the transformed bounding box
            # pad the mins and maxes to ensure the entire mask is included after transforming
            maxes_inc = maxes + 1
            mins_inc = mins - 1
            mins_inc[mins_inc < 0] = 0
            mask = np.copy(
                labels[
                    mins_inc[0] : maxes_inc[0],
                    mins_inc[1] : maxes_inc[1],
                    mins_inc[2] : maxes_inc[2],
                ]
            )
            mask[mask != label_id] = 0
            mask[mask > 0] = 1
            mask_t, _ = transform_image_3d_sitk(
                mask.astype(np.float32), T, interpolator='linear'
            )
            mask_t[mask_t > 0] = 1
            mask_t[mask_t < 0] = 0
            mask_t = mask_t.astype(np.uint8)

            position = self.world_to_roi_coords(mins_t)
            size = maxes_t - mins_t
            roi = MaskROI(position, size, mask_t, label_id)
            self.rois.append(roi)
        self.sort()

    def sort(self):
        """Sorts the ROIs in order of their appearance in the stack."""
        self.rois.sort(key=lambda x: x.z1)

    def set_offset(self, offset):
        """Sets the offset for converting world (napari) coordinates to ROI coordinates.
        Since ROI XY coordinates are relative to the centre of the overview image,
        the XY offset should be -width/2, -height/2, and the Z offset should be the Z coord
        of the first overview image.

        Args:
            offset (array-like): The offset to apply to coordinates (z, y, x).
        """
        self._offset = np.asarray(offset)

    def edit(self, idx, coords):
        """Edits the coordinates of an ROI.

        Args:
            idx (int): Index of the ROI to edit.
            coords (np.ndarray): New coordinates for the ROI.
        """
        coords_roi = self.world_to_roi_coords(coords)
        mins = coords_roi.min(axis=0)
        maxes = coords_roi.max(axis=0)
        self.rois[idx].update_coords(mins, maxes - mins)

    def remove(self, idx):
        """Removes an ROI by index.

        Args:
            idx (int): Index of the ROI to remove.
        """
        del self.rois[idx]

    def clear(self):
        """Clears all ROIs and resets state."""
        self.rois = []
        self.acquiring_rois = set()
        self.acquired_rois = set()
        self._offset = np.asarray([0, 0, 0])

    def update_z_depth(self, z_depth):
        """Updates the state of each ROI based on the current z-depth.

        Args:
            z_depth (float): The current z-depth value.
        """
        self.z_depth = z_depth
        self.remaining_rois = set()
        for roi in self.rois:
            if roi.z1 <= self.z_depth <= roi.z2:
                roi.state = ROIState.ACQUIRING
            elif self.z_depth > roi.z2:
                roi.state = ROIState.ACQUIRED
            else:
                roi.state = ROIState.REMAINING

    def world_to_roi_coords(self, coords):
        """Converts world coordinates to ROI coordinates.

        Args:
            coords (np.ndarray): World coordinates.

        Returns:
            np.ndarray: ROI coordinates.
        """
        return coords + self._offset

    def roi_to_world_coords(self, coords):
        """Converts ROI coordinates to world coordinates.

        Args:
            coords (np.ndarray): ROI coordinates.

        Returns:
            np.ndarray: World coordinates.
        """
        return coords - self._offset


class MaskROI:
    """Class representing a single ROI mask and its properties.

    Attributes:
        id (int): Identifier for the ROI.
        state (ROIState): Current state of the ROI.
        mask (np.ndarray): 3D binary mask of the ROI.
        x1, x2, y1, y2, z1, z2 (float): Bounding box coordinates.
        center (np.ndarray): Center of the ROI.
        size (np.ndarray): Size of the ROI.
    """

    def __init__(self, position, size, mask, id_):
        """Initializes a MaskROI object.

        Args:
            position (np.ndarray): The starting position (z, y, x) of the ROI.
            size (np.ndarray): The size (z, y, x) of the ROI.
            mask (np.ndarray): The 3D binary mask for the ROI.
            id_ (int): The identifier for the ROI.
        """
        self.id = id_
        self.state = ROIState.REMAINING
        self.mask = mask
        self.x1 = position[2]
        self.x2 = position[2] + size[2]
        self.y1 = position[1]
        self.y2 = position[1] + size[1]
        self.z1 = position[0]
        self.z2 = position[0] + size[0]
        self.center = np.array(
            [
                (self.z1 + self.z2) / 2,
                (self.y1 + self.y2) / 2,
                (self.x1 + self.x2) / 2,
            ]
        )
        self.size = size

    def get_current_slice(self, z_depth):
        """Returns the mask slice at the given z-depth.

        Args:
            z_depth (float): The z-depth at which to extract the mask slice.

        Returns:
            np.ndarray: The 2D mask slice at the specified z-depth.
        """
        if not (self.z1 <= z_depth <= self.z2):
            print(
                f'Warning: z_depth not within mask bounds: {z_depth} not in ({self.z1}, {self.z2})'
            )
            return np.zeros_like(self.mask[0])

        mask_z_total = self.z2 - self.z1
        mask_z_cur = z_depth - self.z1
        perc = mask_z_cur / mask_z_total

        # Get the slice index between 0 and self.mask.shape[0] - 1
        idx = round(perc * (self.mask.shape[0] - 1))

        return self.mask[idx]
