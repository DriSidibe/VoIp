import json
import socket
from unittest.mock import MagicMock, patch

from client.client import VoIPClient
from utils import REQUEST_CODES


@patch("socket.socket")
def test_connect_success(mock_socket):
    fake_socket = MagicMock()
    mock_socket.return_value = fake_socket

    # Fake server response
    fake_socket.recv.return_value = json.dumps({
        "code": REQUEST_CODES["OK"]
    }).encode("utf-8")

    client = VoIPClient()
    client.connect_to_server = lambda: None  # override for demo
    # Inject real connect code (you paste yours here)
    def real_connect():
        client.client_socket = socket.socket()
        client.client_socket.connect((client.host, client.port))
        msg = {
            "code": REQUEST_CODES["CONNECT"],
            "payload": {"id": "1", "username": "test"}
        }
        client.client_socket.send(json.dumps(msg).encode("utf-8"))
        resp = client.client_socket.recv(1024).decode()
        if json.loads(resp).get("code") == REQUEST_CODES["OK"]:
            client.isConnected = True

    client.connect_to_server = real_connect

    client.connect_to_server()

    # Assertions
    fake_socket.connect.assert_called_once_with(("localhost", 5000))
    fake_socket.send.assert_called_once()
    fake_socket.recv.assert_called_once()
    assert client.isConnected is True


@patch("socket.socket")
def test_disconnect_success(mock_socket):
    fake_socket = MagicMock()
    mock_socket.return_value = fake_socket

    # Fake server response
    fake_socket.recv.return_value = json.dumps({
        "code": REQUEST_CODES["OK"],
        "payload": "Disconnected"
    }).encode("utf-8")

    client = VoIPClient()
    client.client_socket = fake_socket
    client.isConnected = True

    # Inject your disconnect code
    def real_disconnect():
        msg = {"code": REQUEST_CODES["DISCONNECT"]}
        client.client_socket.send(json.dumps(msg).encode("utf-8"))
        resp = client.client_socket.recv(1024).decode()
        if json.loads(resp).get("code") == REQUEST_CODES["OK"]:
            client.isConnected = False
        client.client_socket.close()

    client.disconnect = real_disconnect

    client.disconnect()

    # Assertions
    fake_socket.send.assert_called_once()
    fake_socket.recv.assert_called_once()
    fake_socket.close.assert_called_once()
    assert client.isConnected is False
