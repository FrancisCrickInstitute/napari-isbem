import napari
from qtpy.QtWidgets import QLabel, QLineEdit, QPushButton, QSpinBox, QGroupBox, QGridLayout, QHBoxLayout
from qtpy.QtCore import Qt
from threading import Thread


class TCPSettings(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 tcp_server,
                 ):
        super().__init__("TCP settings")
        self.viewer = viewer
        self.tcp_server = tcp_server
        self.setLayout(QGridLayout())
        
        self.host_line_edit = QLineEdit(text=self.tcp_server.host)
        self.layout().addWidget(QLabel("Host", alignment=Qt.AlignLeft), 0, 0)
        self.layout().addWidget(self.host_line_edit, 0, 1)

        self.port_spinbox = QSpinBox(maximum=99999, value=self.tcp_server.port)
        self.layout().addWidget(QLabel("Port"), 1, 0)
        self.layout().addWidget(self.port_spinbox, 1, 1)
        
        self.start_server_button = QPushButton("Start server", enabled=True)
        self.start_server_button.clicked.connect(self._on_click_start_server)

        self.stop_server_button = QPushButton("Stop server", enabled=False)
        self.stop_server_button.clicked.connect(self._on_click_stop_server)
        
        layout = QHBoxLayout()
        layout.addWidget(self.start_server_button)
        layout.addWidget(self.stop_server_button)
        self.layout().addLayout(layout, 2, 0, 1, 2)

    def _on_click_start_server(self):
        self.tcp_server.host = self.host_line_edit.text()
        self.tcp_server.port = self.port_spinbox.value()
        self.start_server_button.setEnabled(False)
        self.stop_server_button.setEnabled(True)
        self.host_line_edit.setEnabled(False)
        self.port_spinbox.setEnabled(False)
        thread = Thread(target=self.tcp_server.run)
        thread.start()
        
    def _on_click_stop_server(self):
        self.tcp_server.close()
        self.stop_server_button.setEnabled(False)
        self.start_server_button.setEnabled(True)
        self.host_line_edit.setEnabled(True)
        self.port_spinbox.setEnabled(True)
        