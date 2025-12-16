import datetime
import json
import socket
import threading

from utils import utils, security

client_is_connected = False

class VoIPClient:
    
    def __init__(self, id, host='127.0.0.1', port=8080, username="no username"):
        self.id = id
        self.username = username
        self.host = host
        self.port = port
        self._listeners = []
        self._isConnected = False
        self.message = {}
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_public_key = None
        self.private_key, self.public_key = security.generate_keys()
        self.private_key = security.get_private_key(self.private_key)
        self.public_key = security.get_public_key(self.public_key)
        
        
        self.subscribe(self.on_connection_status_change)
        
    def subscribe(self, callback):
        self._listeners.append(callback)

    def unsubscribe(self, callback):
        self._listeners.remove(callback)

    @property
    def isConnected(self):
        return self._isConnected

    @isConnected.setter
    def isConnected(self, new_value):
        old_value = self._isConnected
        self._isConnected = new_value

        for callback in self._listeners:
            callback(old_value, new_value)
            
    def on_connection_status_change(self, old_value, new_value):
        global client_is_connected
        client_is_connected = new_value
        
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
                self.username = response.get('payload', 'Unknown')
                utils.print_logs_on_terminal(utils.REQUEST_CODES["OK_CONNECT"], "client", self.username)
                self.isConnected = True
                self.server_public_key = response.get("public_key")
                self.get_messages(self.id)
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
            print(payload)
            print("(VoIPClientCLI) ", end='', flush=True)
        
        elif response.get("code") == utils.REQUEST_CODES["OK_CONNECT"]:
            self.username = payload
            print(f"Connected to server as {response.get('payload', 'Unknown')}.")
            print("(VoIPClientCLI) ")
            self.isConnected = True
            self.server_public_key = response.get("public_key")
            
        elif response.get("code") == utils.REQUEST_CODES["OK_DISCONNECT"]:
            self.isConnected = False
            
        elif response.get("code") == utils.REQUEST_CODES["PING"]:
            print("You are still connected.")
            print("(VoIPClientCLI) ")
            
        elif response.get("code") == utils.REQUEST_CODES["BAD_REQUEST"]:
            print(f"Failed to connect: {response.get('payload', 'Unknown error')}")
            print("(VoIPClientCLI) ")
            self.client_socket.close()
            
        elif response.get("code") == utils.REQUEST_CODES["INTERNAL_ERROR"]:
            print("Unknown error occurred.")
            print("(VoIPClientCLI) ")
            
        elif code == utils.REQUEST_CODES["SEND_TEXT"]:
            sender = payload.get("from", "Unknown")
            message = payload.get("message", "")
            print(f"\nNew ~ {sender}: {message}\n(VoIPClientCLI) ", end='', flush=True)
            
        elif code == utils.REQUEST_CODES["MESSAGES_RETRIEVE"]:
            messages = payload.get("messages", [])
            if messages:
                print("Retrieved Messages:")
                for msg in messages:
                    dt = msg.get("datetime", "Unknown time")
                    autor = msg.get("autor", "Unknown")
                    content = msg.get("message", "")
                    print(f"[{dt}] {autor}: {content}")
            else:
                print("No messages found with the given criteria.")
            print("(VoIPClientCLI) ", end='', flush=True)
            
        elif code == utils.REQUEST_CODES["FRIENDS_LIST"]:
            utils.print_friends(payload)

        elif code == utils.REQUEST_CODES["VOICECALL_REQUEST"]:
            who = payload.get("who")
            if not utils.isRinging:
                threading.Thread(target=utils.ring, args=[who]).start()
                utils.isRinging = True
            
    def receive_message_in_external_thread(self, _socket: socket.socket, private_key = None):
        try:
            while self.isConnected:
                response = utils.receive_message(_socket, private_key)
                self.interpret_response(response)
        except socket.error as e:
            self.isConnected = False
        except Exception as e:
            print(f"Error in receiver thread: {e}")
            
    def send_message(self, message: bytes, _socket: socket.socket, public_key = None):
        try:
            utils.send_message(message, _socket, public_key)
        except Exception as e:
            self.client_socket.close()
            self.server_public_key = None
            self.isConnected = False
            print("You're not connected. Maybe a problem with the server !")

    @utils.connection_required(lambda: client_is_connected)
    def voice_call(self, arg):
        parts = arg.split(' ')
        if len(parts) < 1:
            print("Usage: voice_call <recipient_username>")
            return
        recipient_username = parts[0]
        self.message = {
            "code": utils.REQUEST_CODES["VOICECALL_REQUEST"],
            "payload": {
                "id": self.id,
                "who": recipient_username
            },
        }
        self.send_message(utils.encode_message(self.message), self.client_socket, self.server_public_key)

    def disconnect(self):
        self.message = {
            "code": utils.REQUEST_CODES["DISCONNECT"],
            "payload": {
                "id": str(self.id)
            }
        }
        try:
            if self.isConnected:
                self.send_message(utils.encode_message(self.message), self.client_socket, self.server_public_key)
            else:
                print(f"You're not connected.")
            self.client_socket.close()
            self.server_public_key = None
        except socket.error as e:
            self.client_socket.close()
            self.server_public_key = None
            self.isConnected = False
            print(f"Error while disconnecting: {e}")

    def status(self):
        self.message = {
            "code": utils.REQUEST_CODES["PING"],
            "payload": {
                "id": self.id
            },
        }
        self.send_message(utils.encode_message(self.message), self.client_socket, self.server_public_key)

    @utils.connection_required(lambda: client_is_connected) 
    def friends_list(self):
        self.message = {
            "code": utils.REQUEST_CODES["FRIENDS_LIST"],
            "payload": {'id': self.id},
        }
        self.send_message(utils.encode_message(self.message), self.client_socket, self.server_public_key)
            
    @utils.connection_required(lambda: client_is_connected)        
    def text_friend(self, arg):
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
                "message": message
            }
        }
        self.send_message(utils.encode_message(self.message), self.client_socket, self.server_public_key)
            
    @utils.connection_required(lambda: client_is_connected)         
    def get_messages(self, arg=""):
        parts = arg.split(' ')
        if parts[0] == self.id:
            parts = []
        if len(parts) == 0:
            from_date = None
            to_date = None
            from_user = None
        elif len(parts) == 1:
            from_date = parts[0]
            to_date = None
            from_user = None
        elif len(parts) == 2:
            from_date = parts[0]
            to_date = parts[1]
            from_user = None
        else:
            from_date = parts[0]
            to_date = parts[1]
            from_user = parts[2]
        self.message = {
            "code": utils.REQUEST_CODES["MESSAGES_RETRIEVE"],
            "payload": {
                "id": self.id,
                "from_date": from_date if from_date else "",
                "to_date": to_date if to_date else "",
                "from_user": from_user if from_user else ""
            }
        }
        self.send_message(utils.encode_message(self.message), self.client_socket, self.server_public_key)