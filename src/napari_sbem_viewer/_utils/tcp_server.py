import socket
import json

from qtpy.QtCore import QThread


class TCPServer(QThread):
    def __init__(self, host, port, command_trigger, response_queue, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.request_trigger = command_trigger
        self.response_queue = response_queue

        self.is_running = False
        self.response_commands = []
        
    def pause_acquisition(self):
        self.response_commands.append({'msg': 'PAUSE', 'args': [1], 'kwargs': {}})
    
    def delete_all_grids(self):
        self.response_commands.append({'msg': 'DELETE ALL ARRAY GRIDS', 'args': [], 'kwargs': {}})
        
    def add_grid(self, roi_id, x, y, w, h):
        self.response_commands.append({'msg': 'ADD ARRAY GRID', 'args': [None, roi_id, [x, y], [w, h], 0], 'kwargs': {}})
        
    def activate_grid(self, roi_id):
        self.response_commands.append({'msg': 'ACTIVATE ARRAY GRID', 'args': [roi_id], 'kwargs': {}})
        
    def deactivate_grid(self, roi_id):
        self.response_commands.append({'msg': 'DEACTIVATE ARRAY GRID', 'args': [roi_id], 'kwargs': {}})
        
    def activate_overview(self, ov_id):
        self.response_commands.append({'msg': 'ACTIVATE OV', 'args': [ov_id], 'kwargs': {}})
        
    def deactivate_overview(self, ov_id):
        self.response_commands.append({'msg': 'DEACTIVATE OV', 'args': [ov_id], 'kwargs': {}})
        
    def set_slice_thickness(self, thickness):
        self.response_commands.append({'msg': 'SET SLICE THICKNESS', 'args': [thickness], 'kwargs': {}})
    
    def set_overview_interval(self, ov_idx, interval):
        self.response_commands.append({'msg': 'SET OV INTERVAL', 'args': [ov_idx, interval], 'kwargs': {}})
        
    def send_response(self):
        self.response_queue.put({'commands': self.response_commands})
        self.response_commands = []

    def run(self):
        self.is_running = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((self.host, self.port))
            except PermissionError:
                print("RemoteTCP:", "Permission error. Try another port.")
                return
            s.listen()
            s.settimeout(1.0)
            print("RemoteTCP:", f"Listening on {self.host} port {self.port}...")

            while self.is_running:
                try:
                    conn, addr = s.accept()
                    with conn:
                        data = conn.recv(1024)
                        if data:
                            try:
                                request = json.loads(data)
                                
                                print("RemoteTCP:", f"Received: {request}")
                                
                                # Transmit request to main controls
                                self.request_trigger.transmit(request)
                                
                                # Block until the main process processes the data and sends back the result
                                res = self.response_queue.get()
                                print("RemoteTCP:", f"Sending response: {res}")
                                conn.sendall(json.dumps(res).encode('utf-8'))
                                
                            except json.decoder.JSONDecodeError:
                                print("RemoteTCP:", "JSON decode error.")
                                
                except socket.timeout:
                    # Check the flag periodically
                    if not self.is_running:
                        print("RemoteTCP:", "Connection closed.")
                        
                        # Alert the main thread that the connection is closed
                        # self.command_trigger.transmit("STOP SERVER")
                        break
    
    def close(self):
        self.is_running = False
