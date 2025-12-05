import datetime
import json
import socket
import threading

from utils import utils, security


class VoIPClient:
    def __init__(self, id, host='127.0.0.1', port=8080, username="no username"):
        self.id = id
        self.username = username
        self.host = host
        self.port = port
        self.isConnected = False
        self.message = {}
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_public_key = None
        self.private_key, self.public_key = security.generate_keys()
        self.private_key = security.get_private_key(self.private_key)
        self.public_key = security.get_public_key(self.public_key)
        
    def create_connection(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        
    def connect_to_server(self):
        self.message = {
            "code": utils.REQUEST_CODES["CONNECT"],
            "payload": {
                "id": str(self.id),
                "username": str(self.username),
                "public_key": self.public_key.decode('utf-8')
            }
        }
        try:
            self.create_connection()
            response = utils.send_message_and_wait_for_response(utils.encode_message(self.message), self.client_socket)
            response = json.loads(response)
            if response.get("code") == utils.REQUEST_CODES["OK_CONNECT"]:
                print(f"Connected to server as {response.get('payload', 'Unknown')}.")
                self.isConnected = True
                self.server_public_key = response.get("public_key")
                threading.Thread(target=self.receive_message_in_external_thread, daemon=True, args=[self.client_socket, self.private_key]).start()
            else:
                print(f"Failed to connect: {response.get('payload', 'Unknown error')}")
                self.client_socket.close()
        except socket.error as e:
            print(f"Failed to connect to server: Server not available.")
            
    def interpret_response(self, response):
        response = json.loads(response)
        code = response.get("code")
        payload = response.get("payload")
        
        if code == utils.REQUEST_CODES["OK"]:
            utils.print(payload)
            print("(VoIPClientCLI) ", end='', flush=True)
        
        if response.get("code") == utils.REQUEST_CODES["OK_CONNECT"]:
            self.username = response.get('payload', 'no username')
            print(f"Connected to server as {response.get('payload', 'Unknown')}.")
            print("(VoIPClientCLI) ")
            self.isConnected = True
            self.server_public_key = response.get("public_key")
            
        if response.get("code") == utils.REQUEST_CODES["OK_DISCONNECT"]:
            self.isConnected = False
            
        if response.get("code") == utils.REQUEST_CODES["OK_PING"]:
            print("You are still connected.")
            print("(VoIPClientCLI) ")
            
        if response.get("code") == utils.REQUEST_CODES["BAD_REQUEST"]:
            print(f"Failed to connect: {response.get('payload', 'Unknown error')}")
            print("(VoIPClientCLI) ")
            self.client_socket.close()
            
        if response.get("code") == utils.REQUEST_CODES["INTERNAL_ERROR"]:
            print("Unknown error occurred.")
            print("(VoIPClientCLI) ")
            
        if code == utils.REQUEST_CODES["SEND_TEXT"]:
            sender = payload.get("from", "Unknown")
            message = payload.get("message", "")
            datetime_str = payload.get("datetime", "")
            print(f"\nNew message from {sender} at {datetime_str}: {message}\n(VoIPClientCLI) ", end='', flush=True)
            
        if code == utils.REQUEST_CODES["FRIENDS_LIST"]:
            utils.print_friends(payload)
            
    def receive_message_in_external_thread(self, _socket: socket.socket, private_key = None):
        try:
            while self.isConnected:
                response = utils.receive_message(_socket, private_key)
                self.interpret_response(response)
        except socket.error as e:
            print(f"Connection lost: {e}")
            self.isConnected = False

    def disconnect(self):
        self.message = {
            "code": utils.REQUEST_CODES["DISCONNECT"],
            "payload": {
                "id": str(self.id)
            }
        }
        try:
            if self.isConnected:
                utils.send_message(utils.encode_message(self.message), self.client_socket, self.server_public_key)
            else:
                print(f"You're not connected.")
            self.client_socket.close()
            self.server_public_key = None
        except socket.error as e:
            self.client_socket.close()
            self.server_public_key = None
            print(f"Error while disconnecting: {e}")

    def status(self):
        self.message = {
            "code": utils.REQUEST_CODES["PING"],
            "payload": {
                "id": self.id
            }
        }
        try:
            if self.isConnected:
                utils.send_message(utils.encode_message(self.message), self.client_socket, self.server_public_key)
            else:
                print("You are not connected to the server.")
        except socket.error as e:
            print(f"Server not available: {e}")

    def friends_list(self):
        self.message = {
            "code": utils.REQUEST_CODES["FRIENDS_LIST"],
            "payload": {'id': self.id},
            "encrypted": True if self.server_public_key else False
        }
        try:
            if self.isConnected:
                utils.send_message(utils.encode_message(self.message), self.client_socket, self.server_public_key)
            else:
                print("Client is not connected to the server.")
        except socket.error as e:
            print(f"Server not available: {e}")
            
    def text_friend(self, arg):
        try:
            if self.isConnected:
                parts = arg.split(' ')
                if len(parts) < 2:
                    print("Usage: send_text <recipient_username> <message>")
                    return
                recipient_username = parts[0]
                message = ' '.join(parts[1:])
                self.message = {
                    "code": utils.REQUEST_CODES["SEND_TEXT"],
                    "payload": {
                        "id": self.id,
                        "datetime": datetime.datetime.utcnow().isoformat() + "Z",
                        "from": self.username,
                        "to": recipient_username,
                        "message": message,
                        "encrypted": True
                    }
                }
                utils.send_message(utils.encode_message(self.message), self.client_socket, self.server_public_key)
            else:
                print("Client is not connected to the server.")
        except socket.error as e:
            print(f"Server not available: {e}")