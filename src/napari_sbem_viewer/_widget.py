"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""
from typing import TYPE_CHECKING

from skimage.io.collection import alphanumeric_key
from magicgui import magic_factory
from magicgui.widgets import FileEdit
from magicgui.types import FileDialogMode
from qtpy.QtWidgets import QHBoxLayout, QFormLayout, QVBoxLayout, QPushButton, QWidget, QLabel, QLineEdit, QSpinBox, QGroupBox
from qtpy.QtCore import Qt
from napari.qt import thread_worker
import os
import dask.array as da
from dask import delayed
import time
from tifffile import imread
import socket
import json

if TYPE_CHECKING:
    import napari


class SBEMImageIntegration(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        outer_layout = QVBoxLayout()
        
        self.live_viewer = LiveViewer(napari_viewer)
        self.tcp_client = TCPClient(None, None)
        
        # Add host and port form
        tcp_remote_settings_widget = QGroupBox("TCP remote settings")
        client_form = QFormLayout(formAlignment=Qt.AlignLeft)
        self.host_line_edit = QLineEdit(text="localhost")
        self.port_spinbox = QSpinBox(maximum=99999, value=8888)
        client_form.addRow(QLabel("Host", alignment=Qt.AlignLeft), self.host_line_edit)
        client_form.addRow(QLabel("Port"), self.port_spinbox)
        self.save_client_settings_button = QPushButton("Save settings")
        self.save_client_settings_button.clicked.connect(self._on_click_save_client)
        client_form.addRow(self.save_client_settings_button)
        tcp_remote_settings_widget.setLayout(client_form)
        outer_layout.addWidget(tcp_remote_settings_widget)
        
        # Add output directory form
        output_directory_widget = QGroupBox("SBEMImage output directory")
        output_directory_widget_layout = QVBoxLayout()
        self.filename_edit = FileEdit(
            mode=FileDialogMode.EXISTING_DIRECTORY)
        output_directory_widget_layout.addWidget(self.filename_edit.native)
        watch_btn_layout = QHBoxLayout()
        self.watch_btn = QPushButton("Watch folder")
        self.watch_btn.clicked.connect(self._on_click_watch_folder)
        self.stop_watching_btn = QPushButton("Stop watching", enabled=False)
        self.stop_watching_btn.clicked.connect(self._on_click_stop_watching_folder)
        watch_btn_layout.addWidget(self.watch_btn)
        watch_btn_layout.addWidget(self.stop_watching_btn)
        output_directory_widget.setLayout(output_directory_widget_layout)
        output_directory_widget_layout.addLayout(watch_btn_layout)
        outer_layout.addWidget(output_directory_widget)
        
        # Add acquisition settings form
        acquisition_settings_widget = QGroupBox("Acquisition settings")
        acquisition_settings_widget_layout = QVBoxLayout()
        acquisition_form = QFormLayout(formAlignment=Qt.AlignLeft)
        self.coarse_thickness_spinbox = QSpinBox(maximum=999, value=100)
        self.fine_thickness_spinbox = QSpinBox(maximum=999, value=50)
        acquisition_form.addRow(QLabel("Cutting thickness coarse (nm)"), self.coarse_thickness_spinbox)
        acquisition_form.addRow(QLabel("Cutting thickness fine (nm)"), self.fine_thickness_spinbox)
        self.save_acquisition_settings_button = QPushButton("Save settings")
        self.save_acquisition_settings_button.clicked.connect(self._on_click_save_acquisition_settings)
        acquisition_form.addRow(self.save_acquisition_settings_button)
        acquisition_settings_widget_layout.addLayout(acquisition_form)
        acquisition_settings_widget.setLayout(acquisition_settings_widget_layout)
        outer_layout.addWidget(acquisition_settings_widget)
        
        # Add start and stop acquisition buttons
        acquisition_btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start acquisition")
        self.start_btn.clicked.connect(self._on_click_start)
        self.stop_btn = QPushButton("Stop acquisition", enabled=False)
        self.stop_btn.clicked.connect(self._on_click_stop)
        acquisition_btn_layout.addWidget(self.start_btn)
        acquisition_btn_layout.addWidget(self.stop_btn)
        outer_layout.addLayout(acquisition_btn_layout)
        
        self.setLayout(outer_layout)
        
    def _on_click_save_client(self):
        self.tcp_client.host = self.host_line_edit.text()
        self.tcp_client.port = self.port_spinbox.value()
        
    def _on_click_watch_folder(self):
        self.live_viewer.watch_folder(self.filename_edit.value)
        self.watch_btn.setEnabled(False)
        self.stop_watching_btn.setEnabled(True)
        
    def _on_click_stop_watching_folder(self):
        self.live_viewer.stop_watching()
        self.watch_btn.setEnabled(True)
        self.stop_watching_btn.setEnabled(False)
        
    def _on_click_save_acquisition_settings(self):
        self.coarse_thickness = self.coarse_thickness_spinbox.value()
        self.fine_thickness = self.fine_thickness_spinbox.value()
        
    def _on_click_start(self):
        print("Starting acquisition...")
        # TODO: update cutting depths then start acquisition remotely
        if self.tcp_client.send('START'):
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
    
    def _on_click_stop(self):
        print("Stopping acquisition...")
        if self.self.tcp_client.send('PAUSE', 2):
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
        
        
class ROISelection(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        btn = QPushButton("Click me!")
        btn.clicked.connect(self._on_click)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(btn)

    def _on_click(self):
        print("TESTING 0000000")
        print("napari has", len(self.viewer.layers), "layers")
        

class ImageRegistration(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        btn = QPushButton("Click me!")
        btn.clicked.connect(self._on_click)

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(btn)

    def _on_click(self):
        print("TESTING 0000000")
        print("napari has", len(self.viewer.layers), "layers")
        
        
class LiveViewer():
    def __init__(self, napari_viewer):
        self.viewer = napari_viewer
        self.watching = False
        self.time_interval = 1
        self.processed_files = set()
        
    def append(self, delayed_image):
        """Appends the image to viewer.

        Parameters
        ----------
        delayed_image : dask.delayed function object
        """
        if delayed_image is None:
            return

        if self.viewer.layers:
            # layer is present, append to its data
            layer = self.viewer.layers[0]
            image_shape = layer.data.shape[1:]
            image_dtype = layer.data.dtype
            image = da.from_delayed(
                delayed_image, shape=image_shape, dtype=image_dtype,
            ).reshape((1,) + image_shape)
            layer.data = da.concatenate((layer.data, image), axis=0)
        else:
            # first run, no layer added yet
            image = delayed_image.compute()
            image = da.from_delayed(
                delayed_image, shape=image.shape, dtype=image.dtype,
            ).reshape((1,) + image.shape)
            layer = self.viewer.add_image(image, rendering='attenuated_mip')

        # we want to show the last file added in the viewer to do so we want to
        # put the slider at the very end. But, sometimes when user is scrolling
        # through the previous slide then it is annoying to jump to last
        # stack as it gets added. To avoid that jump we 1st check where
        # the scroll is and if its not at the last slide then don't move the slider.
        if self.viewer.dims.point[0] >= layer.data.shape[0] - 2:
            self.viewer.dims.set_point(0, layer.data.shape[0] - 1)
            
    def watch_folder(self, path):
        # TODO: remove layer first if it exists and check for correct file paths and sizes
        # TODO: change name of layer to folder name
        # TODO: if folder is changed then clear processed files

        @thread_worker(connect={'yielded': self.append})
        def _watch_folder():
            """Watches the path for new files and yields it once file is ready.

            Notes
            -----
            Currently, there is no proper way to know if the file has written 
            entirely. So the workaround is we assume that files are generating 
            serially (in most microscopes it common), and files are name in 
            alphanumeric sequence We start loading the total number of minus the 
            last file (`total__files - last`). In other words, once we see the new 
            file in the directory, it means the file before it has completed so load
            that file. For this example, we also assume that the microscope is 
            generating a `final.log` file at the end of the acquisition, this file 
            is an indicator to stop monitoring the directory.

            Parameters
            ----------
            path : str
            directory to monitor and load tiffs as they start appearing.
            """
            current_files = set()
            while self.watching:
                files_to_process = set()
                # Get the all files in the directory at this time
                current_files = set()
                for file in os.listdir(path):
                    if file.endswith('.tif') or file.endswith('.tiff'):
                        current_files.add(file)

                if len(current_files):
                    files_to_process = current_files - self.processed_files

                # yield every file to process as a dask.delayed function object.
                for p in sorted(files_to_process, key=alphanumeric_key):
                    yield delayed(imread)(os.path.join(path, p))
                else:
                    yield

                # add the files which we have yield to the processed list.
                self.processed_files.update(files_to_process)
                time.sleep(self.time_interval)

        _watch_folder()
        self.watching = True

    def stop_watching(self):
        """Stops the watching process.
        """
        self.watching = False
        
        
class TCPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        
    def send(self, msg, *args, **kwargs):
        if self.host is None or self.port is None:
            raise ValueError("Host and port must be set before sending a message.")
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))

            command = {'msg': msg, 'args': args, 'kwargs': kwargs}

            s.sendall(json.dumps(command).encode('utf-8'))
            response = json.loads((s.recv(1024)))
            return response['response']
