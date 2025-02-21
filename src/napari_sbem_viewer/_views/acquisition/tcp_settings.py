from qtpy.QtWidgets import QLabel, QLineEdit, QPushButton, QSpinBox, QGroupBox, QGridLayout, QHBoxLayout, QVBoxLayout
from qtpy.QtCore import Qt


class TCPSettings(QGroupBox):
    def __init__(self):
        super().__init__("TCP settings")
        self.setLayout(QVBoxLayout())
        
        tcp_form_layout = QGridLayout()
        self.host_line_edit = QLineEdit(text='localhost')
        tcp_form_layout.addWidget(QLabel("Host", alignment=Qt.AlignLeft), 0, 0)
        tcp_form_layout.addWidget(self.host_line_edit, 0, 1)
        self.port_spinbox = QSpinBox(maximum=99999, value=8888)
        tcp_form_layout.addWidget(QLabel("Port"), 1, 0)
        tcp_form_layout.addWidget(self.port_spinbox, 1, 1)
        self.layout().addLayout(tcp_form_layout)
        
        tcp_control_layout = QHBoxLayout()
        self.start_server_button = QPushButton("Start server", enabled=True)
        tcp_control_layout.addWidget(self.start_server_button)
        self.stop_server_button = QPushButton("Stop server", enabled=False)
        tcp_control_layout.addWidget(self.stop_server_button)
        self.layout().addLayout(tcp_control_layout)
        