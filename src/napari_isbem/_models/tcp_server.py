import json
import socket
from queue import Queue

from qtpy.QtCore import QThread, Signal


class TCPServer(QThread):
    """Class for managing a TCP server that listens for requests from SBEMimage.

    The server listens for JSON requests with the current SBEMimage state,
    and responds with commands to control the acquisition process. The TCP server
    is designed to run in a separate thread, and blocks until a response is added
    to the response queue. Responses are processed in the main thread using the
    `request_received` signal, which emits the request data to be processed.

    Attributes:
        request_received (Signal): Emitted when a request is received from SBEMimage.
        host (str): The hostname or IP address to bind the server.
        port (int): The port number to bind the server.
        response_queue (Queue): Queue for storing response commands.
        is_running (bool): Indicates if the server is running.
        response_commands (list): List of commands to send as a response.
    """

    request_received = Signal(dict)

    def __init__(self, host, port, parent=None):
        """Initializes the TCPServer.

        Args:
            host (str): Hostname or IP address to bind the server.
            port (int): Port number to bind the server.
            parent (QObject, optional): Parent QObject. Defaults to None.
        """
        super().__init__(parent)
        self.host = host
        self.port = port
        self.response_queue = Queue()

        self.is_running = False
        self.response_commands = []

    def pause_acquisition(self):
        """Appends a PAUSE command to the response commands."""
        self.response_commands.append(
            {'msg': 'PAUSE', 'args': [1], 'kwargs': {}}
        )

    def delete_all_grids(self):
        """Appends a DELETE ALL ARRAY GRIDS command to the response commands."""
        self.response_commands.append(
            {'msg': 'DELETE ALL ARRAY GRIDS', 'args': [], 'kwargs': {}}
        )

    def add_grid(self, roi_id, roi_center, roi_size, ref_center):
        """Appends an ADD ARRAY GRID command to the response commands.

        Args:
            roi_id (int): The ROI identifier.
            roi_center (Any): The center coordinates (in microns) of the ROI relative to the reference image center.
            roi_size (Any): The size of the ROI (in microns).
            ref_center (Any): Position of the reference image center (in microns).
        """
        self.response_commands.append(
            {
                'msg': 'ADD ARRAY GRID',
                'args': [
                    None,
                    roi_id,
                    roi_center,
                    roi_size,
                    ref_center,
                ],
                'kwargs': {},
            }
        )

    def update_grid_tiles_with_mask(self, roi_id, mask):
        """Appends an UPDATE GRID TILES WITH MASK command to the response commands.

        Args:
            roi_id (int): The ROI identifier.
            mask (Any): The 2D binary mask to update grid tiles with.
        """
        self.response_commands.append(
            {
                'msg': 'UPDATE GRID TILES WITH MASK',
                'args': [None, roi_id, mask],
                'kwargs': {},
            }
        )

    def activate_grid(self, roi_id):
        """Appends an ACTIVATE ARRAY GRID command to the response commands.

        Args:
            roi_id (int): The ROI identifier.
        """
        self.response_commands.append(
            {'msg': 'ACTIVATE ARRAY GRID', 'args': [roi_id], 'kwargs': {}}
        )

    def deactivate_grid(self, roi_id):
        """Appends a DEACTIVATE ARRAY GRID command to the response commands.

        Args:
            roi_id (int): The ROI identifier.
        """
        self.response_commands.append(
            {'msg': 'DEACTIVATE ARRAY GRID', 'args': [roi_id], 'kwargs': {}}
        )

    def activate_overview(self, ov_id):
        self.response_commands.append(
            {'msg': 'ACTIVATE OV', 'args': [ov_id], 'kwargs': {}}
        )

    def deactivate_overview(self, ov_id):
        """Appends a DEACTIVATE OV command to the response commands.

        Args:
            ov_id (int): The overview identifier.
        """
        self.response_commands.append(
            {'msg': 'DEACTIVATE OV', 'args': [ov_id], 'kwargs': {}}
        )

    def set_slice_thickness(self, thickness):
        """Appends a SET SLICE THICKNESS command to the response commands.

        Args:
            thickness (float): The slice thickness value.
        """
        self.response_commands.append(
            {'msg': 'SET SLICE THICKNESS', 'args': [thickness], 'kwargs': {}}
        )

    def set_overview_interval(self, ov_idx, interval):
        """Appends a SET OV INTERVAL command to the response commands.

        Args:
            ov_idx (int): The overview index.
            interval (float): The interval value.
        """
        self.response_commands.append(
            {
                'msg': 'SET OV INTERVAL',
                'args': [ov_idx, interval],
                'kwargs': {},
            }
        )

    def send_response(self):
        """Puts the current response commands into the response queue
        and clears the list. This unblocks the TCP server thread which
        sends the response commands back to the client."""
        self.response_queue.put({'commands': self.response_commands})
        self.response_commands = []

    def run(self):
        """Runs the TCP server, listening for incoming requests.
        This can be run in a separate thread with the `start()` method
        inherited from `QThread`."""
        self.is_running = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((self.host, self.port))
            except PermissionError:
                print('RemoteTCP:', 'Permission error. Try another port.')
                return
            s.listen()
            s.settimeout(1.0)
            print(
                'RemoteTCP:', f'Listening on {self.host} port {self.port}...'
            )

            while self.is_running:
                try:
                    conn, addr = s.accept()
                    with conn:
                        data = conn.recv(1024)
                        if data:
                            try:
                                request = json.loads(data)

                                print('RemoteTCP:', f'Received: {request}')

                                # Transmit request to main controls
                                self.request_received.emit(request)

                                # Block until the main process processes the data and sends back the result
                                res = self.response_queue.get()
                                conn.sendall(json.dumps(res).encode('utf-8'))

                                # Remove the 'mask' attribute from the response before printing
                                for cmd in res['commands']:
                                    if (
                                        cmd['msg']
                                        == 'UPDATE GRID TILES WITH MASK'
                                    ):
                                        if len(cmd['args']) == 3:
                                            cmd['args'][2] = 'MASK'
                                        elif 'mask' in cmd['kwargs']:
                                            cmd['kwargs']['mask'] = 'MASK'
                                print('RemoteTCP:', f'Sent response: {res}')

                            except json.decoder.JSONDecodeError:
                                print('RemoteTCP:', 'JSON decode error.')

                except socket.timeout:
                    # Check the flag periodically
                    if not self.is_running:
                        print('RemoteTCP:', 'Connection closed.')
                        break

    def close(self):
        """Stops the TCP server."""
        self.is_running = False
