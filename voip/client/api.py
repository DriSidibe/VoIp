import json
import socket

REQUEST_CODES = {
    "OK": 200,
    "BAD_REQUEST": 400,
    "NOT_FOUND": 404,
    "INTERNAL_ERROR": 500,
    "CLOSE": 600,
    "PING": 700,
    "CONNECT": 800,
    "DISCONNECT": 900,
    "FRIENDS_LIST": 1000
}

def print_friends(friends):
    if friends:
        print("Available friends on the server:")
        for friend in friends:
            print(f"- {friend}")
    else:
        print("No friends available on the server.")

class VoIPClient:
    def __init__(self, id, host='127.0.0.1', port=8080, username="no username"):
        self.id = id
        self.username = username
        self.host = host
        self.port = port
        self.isConnected = False
        self.message = {}
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect_to_server(self):
        self.message = {
            "code": REQUEST_CODES["CONNECT"],
            "payload": {
                "id": str(self.id),
                "username": str(self.username)
            }
        }
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            response = self.send_message(json.dumps(self.message))
            response = json.loads(response)
            if response.get("code") == REQUEST_CODES["OK"]:
                print(f"Connected to server as {response.get('payload', 'Unknown')}.")
                self.isConnected = True
            else:
                print(f"Failed to connect: {response.get('payload', 'Unknown error')}")
                self.client_socket.close()
        except socket.error as e:
            print(f"Failed to connect to server: Server not available.")

    def disconnect(self):
        self.message = {
            "code": REQUEST_CODES["DISCONNECT"],
            "payload": {
                "id": str(self.id)
            }
        }
        try:
            if self.isConnected:
                response = self.send_message(json.dumps(self.message))
                print(json.loads(response).get("payload"))
                if json.loads(response).get("code") == REQUEST_CODES["OK"]:
                    self.isConnected = False
            else:
                print(f"You're not connected.")
            self.client_socket.close()
        except socket.error as e:
            self.client_socket.close()
            print(f"Error while disconnecting: {e}")

    def status(self):
        self.message = {
            "code": REQUEST_CODES["PING"],
            "payload": {}
        }
        try:
            if self.isConnected:
                response = self.send_message(json.dumps(self.message))
                if json.loads(response).get("code") == REQUEST_CODES["OK"]:
                    print("Client is connected to the server.")
                else:
                    print("Client is not connected to the server.")
            else:
                print("Client is not connected to the server.")
        except socket.error as e:
            print(f"Server not available: {e}")

    def friends_list(self):
        self.message = {
            "code": REQUEST_CODES["FRIENDS_LIST"],
            "payload": {'id': self.id}
        }
        try:
            if self.isConnected:
                response = self.send_message(json.dumps(self.message))
                if json.loads(response).get("code") == REQUEST_CODES["OK"]:
                    print_friends(json.loads(response).get("payload"))
                else:
                    print("An error occurred while fetching friends list.")
            else:
                print("Client is not connected to the server.")
        except socket.error as e:
            print(f"Server not available: {e}")

    def send_message(self, message):
        try:
            self.client_socket.send(message.encode('utf-8'))
            return self.client_socket.recv(1024).decode('utf-8')
        except socket.error as e:
            raise e