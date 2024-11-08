import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from napari.qt import create_worker

from napari_sbem_viewer._widgets.sbemimage_integration import TCPSettings, AcquisitionSettings, AcquisitionInfo
from napari_sbem_viewer._utils.acquisition_model import AcquisitionModel
from napari_sbem_viewer._utils.live_viewer import LiveViewer
from napari_sbem_viewer._utils.tcp_server import TCPServer
from napari_sbem_viewer._utils.roi_data import ROIData, ROIState
from napari_sbem_viewer._utils.general_utils import Trigger, is_multiple


class SBEMimageIntegration(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.live_viewer = LiveViewer(self.viewer)
        self.acquisition_model = AcquisitionModel(self.live_viewer)
        self.tcp_settings = TCPSettings()
        self.acquisition_settings = AcquisitionSettings(self.viewer)
        self.acquisition_info = AcquisitionInfo()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.tcp_settings)
        self.layout().addWidget(self.acquisition_settings)
        self.layout().addWidget(self.acquisition_info)
        self.layout().addStretch(1)
        
        # Init acquisition model
        self.acquisition_model.acquisition_info_updated.connect(self.acquisition_info.update_acquisition_info)
        self.acquisition_model.overviews_updated.connect(self.acquisition_settings.update_overview_dirs)
        self.acquisition_model.rois_updated.connect(self.acquisition_info.update_roi_info)
        self.acquisition_model._on_fine_thickness_changed(self.acquisition_settings.fine_thickness_spinbox.value())
        self.acquisition_model.errored.connect(self._show_error)

        # Init tcp settings
        self.tcp_settings.start_server_button.clicked.connect(self._on_click_start_server)
        self.tcp_settings.stop_server_button.clicked.connect(self._on_click_stop_server)
        
        # Init acquisition settings
        self.acquisition_settings.roi_combo_box.currentIndexChanged.connect(lambda: self.acquisition_model._on_roi_layer_changed(self.acquisition_settings.get_roi_layer()))
        self.acquisition_settings.overview_combo_box.currentIndexChanged.connect(self._on_change_ov_combo)
        self.acquisition_settings.fine_thickness_spinbox.valueChanged.connect(self.acquisition_model._on_fine_thickness_changed)

        # Init viewer events
        self.viewer.layers.events.removed.connect(self._update_roi_selections)
        self.viewer.layers.events.inserted.connect(self._update_roi_selections)
        self._update_roi_selections()
        
    def _on_click_start_server(self):
        self.acquisition_model.tcp_server.host = self.tcp_settings.host_line_edit.text()
        self.acquisition_model.tcp_server.port = self.tcp_settings.port_spinbox.value()
        self.acquisition_model.tcp_server.start()
        self.tcp_settings.start_server_button.setEnabled(False)
        self.tcp_settings.stop_server_button.setEnabled(True)
        self.tcp_settings.host_line_edit.setEnabled(False)
        self.tcp_settings.port_spinbox.setEnabled(False)
        
    def _on_click_stop_server(self):
        self.acquisition_model.tcp_server.close()
        self.acquisition_model.tcp_server.wait()
        self.tcp_settings.stop_server_button.setEnabled(False)
        self.tcp_settings.start_server_button.setEnabled(True)
        self.tcp_settings.host_line_edit.setEnabled(True)
        self.tcp_settings.port_spinbox.setEnabled(True)
        
    def _on_select_overview_dir(self, ov_dir):
        try:
            self.live_viewer.init_images(ov_dir)
        except ValueError as e:
            QMessageBox.warning(self, "Error adding images", str(e))
            self.acquisition_settings.overview_combo_box.setCurrentIndex(0)
            return
        self.acquisition_settings.roi_combo_box.setEnabled(True)
        self.acquisition_settings.coarse_thickness_label.setText(f"{self.live_viewer.pixel_size_z*1e3:.0f}")
        create_worker(self.live_viewer.watch_folder, 
                      ov_dir, 
                      _connect={'yielded': self.live_viewer.append, 'errored': self._handle_overview_error})

    def _on_change_ov_combo(self):
        self._on_reset_overview()
        if self.acquisition_settings.overview_combo_box.currentIndex() < 1:
            return
        self._on_select_overview_dir(self.acquisition_settings.overview_combo_box.currentText())
        
    def _on_reset_overview(self):
        self.live_viewer.reset()
        self.acquisition_settings.roi_combo_box.setCurrentIndex(0)
        self.acquisition_settings.roi_combo_box.setEnabled(False)
        self.acquisition_settings.coarse_thickness_label.setText("")
            
    # def _update_rois(self, event):
    #     if not hasattr(event, 'action'):
    #         return
    #     if event.action == ActionType.ADDED:
    #         for idx in event.data_indices:
    #             self.roi_data.add_bounding_box(self.roi_layer.data[idx])
    #     elif event.action == ActionType.REMOVED:
    #         for idx in event.data_indices:
    #             self.roi_data.remove(idx)
    #     elif event.action == ActionType.CHANGED:
    #         for idx in event.data_indices:
    #             self.roi_data.edit(idx, self.roi_layer.data[idx])
    #     self.acquisition_info.update_roi_info(self.roi_data)
                
    def _update_roi_selections(self):
        layer_names = self.acquisition_settings._get_roi_layer_names()
        roi_layer = self.acquisition_settings.roi_combo_box.currentText()
        self.acquisition_settings.roi_combo_box.clear()
        self.acquisition_settings.roi_combo_box.addItem("")
        self.acquisition_settings.roi_combo_box.addItems(layer_names)
    
        # if the selected layer has been deleted, unselect from the combo boxes
        if self.acquisition_settings.roi_combo_box.currentText() not in layer_names:
            self.acquisition_settings.roi_combo_box.setCurrentIndex(0)
            self.acquisition_model.roi_data.clear()
        else:
            self.acquisition_settings.roi_combo_box.setCurrentText(roi_layer)
    
    def _show_error(self, title, text):
        QMessageBox.warning(self, title, text)
    
    def _handle_overview_error(self, error):
        self._show_error("Error adding images", error)
        self.acquisition_settings.overview_combo_box.setCurrentIndex(0)
        