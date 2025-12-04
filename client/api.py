import json
import socket

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
            if response.get("code") == utils.REQUEST_CODES["OK"]:
                print(f"Connected to server as {response.get('payload', 'Unknown')}.")
                self.isConnected = True
                self.server_public_key = response.get("public_key")
            else:
                print(f"Failed to connect: {response.get('payload', 'Unknown error')}")
                self.client_socket.close()
        except socket.error as e:
            print(f"Failed to connect to server: Server not available.")

    def disconnect(self):
        self.message = {
            "code": utils.REQUEST_CODES["DISCONNECT"],
            "payload": {
                "id": str(self.id)
            }
        }
        try:
            if self.isConnected:
                response = utils.send_message_and_wait_for_response(utils.encode_message(self.message), self.client_socket, self.private_key, self.server_public_key)
                print(json.loads(response).get("payload"))
                if json.loads(response).get("code") == utils.REQUEST_CODES["OK"]:
                    self.isConnected = False
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
            "payload": {}
        }
        try:
            if self.isConnected:
                response = utils.send_message_and_wait_for_response(utils.encode_message(self.message), self.client_socket, self.private_key, self.server_public_key)
                if json.loads(response).get("code") == utils.REQUEST_CODES["OK"]:
                    print("Client is connected to the server.")
                else:
                    print("Client is not connected to the server.")
            else:
                print("Client is not connected to the server.")
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
                response = utils.send_message_and_wait_for_response(utils.encode_message(self.message), self.client_socket, self.private_key, self.server_public_key)
                if json.loads(response).get("code") == utils.REQUEST_CODES["OK"]:
                    utils.print_friends(json.loads(response).get("payload"))
                else:
                    print("An error occurred while fetching friends list.")
            else:
                print("Client is not connected to the server.")
        except socket.error as e:
            print(f"Server not available: {e}")
            
    def text_friend(self, arg):
        try:
            if self.isConnected:
                parts = arg.split(' ', 1)
                if len(parts) != 2:
                    print("Usage: send_text <recipient_username> <message>")
                    return
                recipient_username, message = parts
                self.message = {
                    "code": utils.REQUEST_CODES["SEND_TEXT"],
                    "payload": {
                        "to": recipient_username,
                        "message": message,
                        "encrypted": True if self.server_public_key else False
                    }
                }
                response = utils.send_message_and_wait_for_response(utils.encode_message(self.message), self.client_socket, self.private_key, self.server_public_key)
                response = json.loads(response)
                if response.get("code") == utils.REQUEST_CODES["OK"]:
                    print(f"Message sent to {recipient_username}.")
                else:
                    print(f"Failed to send message: {response.get('payload', 'Unknown error')}")
            else:
                print("Client is not connected to the server.")
        except socket.error as e:
            print(f"Server not available: {e}")