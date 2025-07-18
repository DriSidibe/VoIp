import json
import socket

class VoIPClient:
    def __init__(self, id, host='127.0.0.1', port=8080, username="no username"):
        self.id = id
        self.username = username
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.isConnected = False
        self.message = {
            "type": "connect",
            "payload": {
                "id": str(self.id),
                "username": str(self.username)
            }
        }

    def connect_to_server(self):
        try:
            self.client_socket.connect((self.host, self.port))
            self.client_socket.send(json.dumps(self.message).encode('utf-8'))
            response = self.client_socket.recv(1024).decode('utf-8')
            if json.loads(response).get("status") == "OK":
                print(f"Connected to server as {self.username}.")
                self.isConnected = True
        except socket.error as e:
            print(f"Failed to connect to server: {e}")

    def disconnect(self):
        try:
            if self.isConnected:
                self.message["type"] = "disconnect"
                self.client_socket.send(json.dumps(self.message).encode('utf-8'))
                response = self.client_socket.recv(1024).decode('utf-8')
                if json.loads(response).get("status") == "OK":
                    print(f"Disconnected from server approved.")
                    self.isConnected = False
                    self.client_socket.shutdown(socket.SHUT_RDWR)
                    self.client_socket.close()
            else:
                print(f"Failed to disconnect.")
        except socket.error as e:
            print(f"Error while disconnecting: {e}")

    def send_message(self, message):
        try:
            self.client_socket.send(message.encode('utf-8'))
            response = self.client_socket.recv(1024).decode('utf-8')
            print(f"Received from server: {response}")
        except socket.error as e:
            print(f"Server not available: {e}")