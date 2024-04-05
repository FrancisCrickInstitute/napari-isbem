import socket
import json


class TCPServer:
    def __init__(self, host, port, command_trigger, response_queue):
        self.host = host
        self.port = port
        self.request_trigger = command_trigger
        self.response_queue = response_queue

        self.is_running = False

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
