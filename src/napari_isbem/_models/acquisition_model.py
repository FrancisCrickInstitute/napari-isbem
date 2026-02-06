import numpy as np
from napari.layers import Labels
from qtpy.QtCore import QObject, Signal

from napari_isbem._models.live_viewer import (
    LiveViewer,
    LiveViewerNotInitializedError,
)
from napari_isbem._models.roi_data import ROIData, ROIState
from napari_isbem._models.tcp_server import TCPServer
from napari_isbem._utils.general_utils import is_multiple


class AcquisitionModel(QObject):
    """Model for managing SBEM acquisition logic and state.

    This class coordinates the interaction between the napari viewer, ROI management,
    TCP server communication, and live image acquisition. It handles requests from
    the TCP server, updates ROI states, manages acquisition parameters, and emits
    signals to update the GUI and other components.

    Attributes:
        errored (Signal): Emitted when an error occurs, with a title and message.
        acquisition_info_updated (Signal): Emitted when acquisition info is updated (z_depth, slice_thickness, paused).
        rois_updated (Signal): Emitted when ROI data is updated.
        viewer: The napari viewer instance.
        layer_model: The model managing napari layers.
        tcp_server: TCPServer instance for communication.
        roi_data: ROIData instance for managing ROIs.
        live_viewer: LiveViewer instance for live image acquisition.
        fine_thickness: The fine section thickness for acquisition.
        is_cutting_thin (bool): Whether thin sectioning is currently active.
        last_z_depth: Last received z-depth value.
        pause_before_acquire_roi (bool): Whether to pause before acquiring a new ROI.
        pause_after_acquire_roi (bool): Whether to pause after acquiring a ROI.
        reset_rois (bool): Whether to reset ROIs in SBEMimage.
    """

    errored = Signal(str, str)
    acquisition_info_updated = Signal(float, float, bool)
    rois_updated = Signal(ROIData)

    def __init__(self, viewer, layer_model):
        """Initializes the AcquisitionModel.

        Args:
            viewer: The napari viewer instance.
            layer_model: The model managing napari layers.
        """
        super().__init__()
        self.viewer = viewer
        self.layer_model = layer_model
        self.tcp_server = TCPServer('localhost', 8888)
        self.roi_data = ROIData()
        self.live_viewer = LiveViewer(self.viewer, 'EM overview')
        self.fine_thickness = None
        self.is_cutting_thin = False
        self.last_z_depth = None
        self.pause_before_acquire_roi = False
        self.pause_after_acquire_roi = False
        self.reset_rois = True
        self.tcp_server.request_received.connect(self.process_request)
        self.live_viewer.initialized.connect(self.layer_model.add_em_layer)
        self.live_viewer.cleared.connect(self.layer_model.remove_em_layer)

    def process_request(self, request):
        """Processes an acquisition request from the TCP server.

        This method is called when a request is received from SBEMimage.
        It processes the request and adds the necessary commands to the
        TCP server using the current z-depth and ROI information.

        Args:
            request (dict): Dictionary containing 'slice_thickness', 'z_depth', and 'paused' keys.

        Emits:
            acquisition_info_updated: With z_depth, slice_thickness, and paused status.
            rois_updated: With updated ROIData.
            errored: If an error occurs during processing.
        """
        try:
            slice_thickness = request['slice_thickness']
            z_depth = request['z_depth']
            is_paused = request['paused']

            # emit signals to update the GUI
            self.acquisition_info_updated.emit(
                z_depth, slice_thickness, is_paused
            )
            self.last_z_depth = z_depth

            if not self.live_viewer.is_initialized():
                raise LiveViewerNotInitializedError(
                    'Select overview directory before using TCP'
                )

            # check if fine thickness is a multiple of coarse thickness
            self._check_fine_thickness()

            # add response commands
            self._update_rois(z_depth)
            self._update_cutting_depth(z_depth)

            # emit signal with updated ROI information
            self.rois_updated.emit(self.roi_data)

        except LiveViewerNotInitializedError as e:
            self.errored.emit('LiveViewer error', str(e))
            self.tcp_server.pause_acquisition()
        except Exception as e:
            self.errored.emit('Acquisition error', str(e))
            self.tcp_server.pause_acquisition()
            raise

        finally:
            self.tcp_server.send_response()

    def set_roi_layer(self, roi_layer):
        """Sets the ROI layer and updates ROI data accordingly.

        Args:
            roi_layer (Labels or None): The napari Labels layer containing ROI masks,
                or None to clear ROIs.

        Emits:
            rois_updated: With updated ROIData.
        """
        self.roi_data.clear()

        if roi_layer is not None:
            self.roi_data.set_offset(
                [
                    self.live_viewer.position_z,
                    -self.live_viewer.size_y // 2,
                    -self.live_viewer.size_x // 2,
                ]
            )

            # if the roi layer exists, update the roi data
            if isinstance(roi_layer, Labels):
                self.roi_data.add_masks(roi_layer)

            # update the acquisition state of the rois using previous z-depth
            if self.last_z_depth is not None:
                self.roi_data.update_z_depth(self.last_z_depth)

            # don't reset ROIs in SBEMimage after setting the ROI layer
            self.reset_rois = False

        else:
            self.reset_rois = True

        self.rois_updated.emit(self.roi_data)

    def set_fine_thickness(self, fine_thickness):
        self.fine_thickness = fine_thickness

    def get_viewer_z_depth(self):
        """Gets the current z-depth in world coordinates from the viewer.

        Returns:
            float: The current z-depth in world coordinates.
        """
        return self.viewer.dims.point[0] + self.live_viewer.position_z

    def focus_on_roi(self, idx, region='center'):
        """Centers the napari viewer on the specified ROI and region.

        Args:
            idx (int): Index of the ROI to focus on.
            region (str): Region of the ROI to focus on ('center', 'top', or 'bottom').

        Raises:
            ValueError: If an invalid region is specified.
        """
        roi = self.roi_data.rois[idx]
        if region == 'center':
            z = roi.center[0]
        elif region == 'top':
            z = roi.z2
        elif region == 'bottom':
            z = roi.z1
        else:
            raise ValueError(f'Invalid region: {region}')
        coords = self.roi_data.roi_to_world_coords(
            np.array([z, roi.center[1], roi.center[2]])
        )
        self.viewer.camera.center = coords
        self.viewer.dims.set_point(0, coords[0])

    def reset_view(self):
        """Resets the napari viewer and focusses on the most recent slice in the live viewer."""
        self.viewer.reset_view()
        self.live_viewer.reset_z_view()

    def _update_rois(self, z_depth):
        if self.reset_rois:
            self.tcp_server.delete_all_grids()
        self.roi_data.update_z_depth(z_depth)
        for roi in self.roi_data.rois:
            y, x = roi.center[1:]
            h, w = roi.size[1:]
            # get center position from default (top-left) position as reference for ROIs
            ref_center = (np.array([self.live_viewer.position_x, self.live_viewer.position_y]) +
                          np.array([self.live_viewer.size_x, self.live_viewer.size_y]) / 2)
            self.tcp_server.add_grid(
                roi.id,
                [float(x), float(y)],
                [float(w), float(h)],
                ref_center.tolist(),
            )
            if roi.state == ROIState.ACQUIRING:
                self.tcp_server.activate_grid(roi.id)
                self.tcp_server.update_grid_tiles_with_mask(
                    roi.id, roi.get_current_slice(z_depth).tolist()
                )
                # if new roi is reached
                if roi.id not in self.roi_data.acquiring_rois:
                    self.roi_data.acquiring_rois.add(roi.id)
                    if self.pause_before_acquire_roi:
                        self.tcp_server.pause_acquisition()
            else:
                self.tcp_server.deactivate_grid(roi.id)
                # if the roi has been fully imaged
                if roi.id in self.roi_data.acquiring_rois:
                    self.roi_data.acquiring_rois.remove(roi.id)
                    if self.pause_after_acquire_roi:
                        self.tcp_server.pause_acquisition()

    def _update_cutting_depth(self, z_depth):
        if self.roi_data.acquiring_rois:
            self.is_cutting_thin = True

        if self.roi_data.acquiring_rois:
            self.tcp_server.set_slice_thickness(int(self.fine_thickness))

        # only set the cutting depth back to coarse thickness if the current depth is a multiple of coarse thickness
        elif is_multiple(
            z_depth - self.live_viewer.position_z,
            self.live_viewer.pixel_size_z,
        ):
            self.tcp_server.set_slice_thickness(
                int(self.live_viewer.pixel_size_z * 1e3)
            )
            self.is_cutting_thin = False

    def _check_fine_thickness(self):
        if self.fine_thickness is None:
            raise ValueError('Fine thickness is not set.')
        coarse_thickness = self.live_viewer.pixel_size_z * 1e3
        if coarse_thickness % self.fine_thickness != 0:
            raise ValueError(
                'Fine thickness must be a multiple of coarse thickness.'
            )
