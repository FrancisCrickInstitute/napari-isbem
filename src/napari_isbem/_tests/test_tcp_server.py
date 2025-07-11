import json
import time

import pytest

from napari_isbem._models.tcp_server import TCPServer


@pytest.fixture
def tcp_server():
    server = TCPServer(host='127.0.0.1', port=5000)
    yield server
    server.close()


def test_pause_acquisition(tcp_server):
    tcp_server.pause_acquisition()
    assert tcp_server.response_commands == [
        {'msg': 'PAUSE', 'args': [1], 'kwargs': {}}
    ]


def test_delete_all_grids(tcp_server):
    tcp_server.delete_all_grids()
    assert tcp_server.response_commands == [
        {'msg': 'DELETE ALL ARRAY GRIDS', 'args': [], 'kwargs': {}}
    ]


def test_add_grid(tcp_server):
    tcp_server.add_grid(
        roi_id=1, roi_center=(0, 0), roi_size=(10, 10), ov_position=(5, 5)
    )
    assert tcp_server.response_commands == [
        {
            'msg': 'ADD ARRAY GRID',
            'args': [None, 1, (0, 0), (10, 10), (5, 5)],
            'kwargs': {},
        }
    ]


def test_update_grid_tiles_with_mask(tcp_server):
    tcp_server.update_grid_tiles_with_mask(roi_id=1, mask=[[1, 0], [0, 1]])
    assert tcp_server.response_commands == [
        {
            'msg': 'UPDATE GRID TILES WITH MASK',
            'args': [None, 1, [[1, 0], [0, 1]]],
            'kwargs': {},
        }
    ]


def test_activate_grid(tcp_server):
    tcp_server.activate_grid(roi_id=1)
    assert tcp_server.response_commands == [
        {'msg': 'ACTIVATE ARRAY GRID', 'args': [1], 'kwargs': {}}
    ]


def test_deactivate_grid(tcp_server):
    tcp_server.deactivate_grid(roi_id=1)
    assert tcp_server.response_commands == [
        {'msg': 'DEACTIVATE ARRAY GRID', 'args': [1], 'kwargs': {}}
    ]


def test_activate_overview(tcp_server):
    tcp_server.activate_overview(ov_id=1)
    assert tcp_server.response_commands == [
        {'msg': 'ACTIVATE OV', 'args': [1], 'kwargs': {}}
    ]


def test_server_receives_and_sends_data(tcp_server, mocker):
    mock_socket = mocker.patch('socket.socket')
    mock_conn = mocker.MagicMock()
    mock_socket.return_value.__enter__.return_value.accept.return_value = (
        mock_conn,
        ('127.0.0.1', 12345),
    )
    mock_conn.recv.return_value = json.dumps({'command': 'TEST'}).encode(
        'utf-8'
    )
    mock_conn.sendall = mocker.MagicMock()

    # Start the server in a separate thread
    tcp_server.start()
    tcp_server.pause_acquisition()
    tcp_server.send_response()

    # Allow some time for the server to start
    time.sleep(1.5)

    # Stop the server after processing one request
    tcp_server.close()

    # Check that the response was sent
    mock_conn.sendall.assert_called_once_with(
        json.dumps(
            {'commands': [{'msg': 'PAUSE', 'args': [1], 'kwargs': {}}]}
        ).encode('utf-8')
    )
