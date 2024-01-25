import napari
from qtpy.QtWidgets import QLabel, QLineEdit, QPushButton, QSpinBox, QGroupBox, QGridLayout
from qtpy.QtCore import Qt


class TCPSettings(QGroupBox):
    def __init__(self,
                 viewer: napari.Viewer,
                 tcp_client,
                 ):
        super().__init__("TCP settings")
        self.viewer = viewer
        self.tcp_client = tcp_client
        self.setLayout(QGridLayout())
        
        self.host_line_edit = QLineEdit(text=self.tcp_client.host)
        self.host_line_edit.textChanged.connect(self._on_change_setting)
        self.layout().addWidget(QLabel("Host", alignment=Qt.AlignLeft), 0, 0)
        self.layout().addWidget(self.host_line_edit, 0, 1)

        self.port_spinbox = QSpinBox(maximum=99999, value=self.tcp_client.port)
        self.port_spinbox.valueChanged.connect(self._on_change_setting)
        self.layout().addWidget(QLabel("Port"), 1, 0)
        self.layout().addWidget(self.port_spinbox, 1, 1)
        
        self.save_client_settings_button = QPushButton("Save settings", enabled=False)
        self.save_client_settings_button.clicked.connect(self._on_click_save_client)
        self.layout().addWidget(self.save_client_settings_button, 2, 0, 1, 2)

    def _on_click_save_client(self):
        self.tcp_client.host = self.host_line_edit.text()
        self.tcp_client.port = self.port_spinbox.value()
        self.save_client_settings_button.setEnabled(False)
        
    def _on_change_setting(self):
        self.save_client_settings_button.setEnabled(True)
        