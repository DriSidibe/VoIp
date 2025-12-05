import datetime
import socket
import logging
import json
import threading

from utils import utils, security as sc

class VoIPServer(socket.socket):
    """Simple client-server application class."""

    _instance = None

    def __new__(cls, host: str, port: int):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            return cls._instance
        
    def __init__(self, host: str, port: int):
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        if not hasattr(self, '_initialized'):
            self._initialized = True
        self.bind((self.host, self.port))
        self.main_listenning_thread = None
        self.clients = []
        self.available_clients = []
        self.private_key, self.public_key = sc.generate_keys()
        self.private_key = sc.get_private_key(self.private_key)
        self.public_key = sc.get_public_key(self.public_key)

        self.logger = logging.getLogger("VoIPServer")
        self.logger.setLevel(logging.DEBUG)
        self.file_handler = logging.FileHandler("VoIPServer.log")
        self.file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.file_handler.setFormatter(formatter)
        self.logger.addHandler(self.file_handler)

        self.running = False

        self.load_clients()

    def _listen(self):
        while True:
            client_socket, addr = self.accept()
            data = utils.receive_message(client_socket)
            data = json.loads(data)

            if(data.get("code") == utils.REQUEST_CODES["CONNECT"]):
                response = self.connect(data['payload']['id'], client_socket, data['payload'].get('public_key'))
                utils.send_message(utils.encode_message(response), client_socket)
                if response.get("code") == utils.REQUEST_CODES["OK_CONNECT"]:
                    t = threading.Thread(target=self._listen_client, daemon=True, args=[client_socket,])
                    t.start()

        #self.logger.info(f"Server stopped at {datetime.datetime.now}")

    def close_server(self, client_socket: socket.socket):
        pass
    
    def ping(self, client_socket: socket.socket, interlaucutor: dict):
        utils.send_message(utils.encode_message({"code": utils.REQUEST_CODES["PING"]}), client_socket, interlaucutor.get("public_key", None))
        
    def disconnect_client(self, client_socket: socket.socket, data, interlaucutor: dict):
        message = {
            "code": utils.REQUEST_CODES["OK"],
            "payload": f"Client {data['payload']['id']} disconnected."
        }
        utils.send_message(utils.encode_message(message), client_socket, interlaucutor.get("public_key", None))
        print(f"Disconnecting client {data['payload']['id']}...")
        response = self.disconnect(data['payload']['id'], client_socket)
        if(response.get("code") == utils.REQUEST_CODES["OK"]):
            return 1
        else:
            utils.send_message(utils.encode_message(response), client_socket, interlaucutor.get("public_key", None))
        return -1
    
    def get_friends_list(self, client_socket: socket.socket, data, interlaucutor: dict):
        friends = [client['username'] for client in self.available_clients if client.get('id') != data['payload'].get('id')]
        if not friends:
            friends = []
        message = {
            "code": utils.REQUEST_CODES["FRIENDS_LIST"],
            "payload": friends,
        }
        utils.send_message(utils.encode_message(message), client_socket, interlaucutor.get("public_key", None))
        
    def send_text(self, client_socket: socket.socket, data, interlaucutor: dict):
        recipient_username = data['payload'].get('to')
        message_text = data['payload'].get('message')
        _datetime = data['payload'].get('datetime')
        sender_username = data['payload'].get('from', 'Unknown')

        recipient_client = [client for client in self.available_clients if client['username'] == recipient_username]
        recipient_client = recipient_client[0] if recipient_client else None
        ack_message = {}
        if recipient_client:
            message = {
                "code": utils.REQUEST_CODES["SEND_TEXT"],
                "payload": {
                    "from": sender_username,
                    "message": message_text,
                    "datetime": _datetime
                },
            }
            utils.store_message(sender_username, recipient_username, _datetime, message_text)
            utils.send_message(utils.encode_message(message), recipient_client['socket'], recipient_client.get("public_key", None))
            ack_message = {
                "code": utils.REQUEST_CODES["OK"],
                "payload": f"Message sent to {recipient_username}."
            }
        else:
            ack_message = {
                "code": utils.REQUEST_CODES["NOT_FOUND"],
                "payload": f"Recipient {recipient_username} not found."
            }
        utils.send_message(utils.encode_message(ack_message), client_socket, interlaucutor.get("public_key", None))
        
    def get_messages(self, client_socket: socket.socket, data, interlaucutor: dict):
        messages = utils.get_messages(interlaucutor, data.get("from_date"), data.get("to_date"), data.get("from_user"))
        message = {
                "code": utils.REQUEST_CODES["MESSAGES_RETRIEVE"],
                "payload": {
                    "messages": messages
                }
            }
        utils.send_message(utils.encode_message(message), client_socket, interlaucutor.get("public_key", None))

    def _listen_client(self, client_socket: socket.socket):
        try:
            while True:
                data = utils.receive_message(client_socket, self.private_key)
                data = json.loads(data)
                
                interlaucutor = [client for client in self.available_clients if client.get('id') == data['payload'].get('id')]
                interlaucutor = interlaucutor[0] if interlaucutor else {}
                

                if(data.get("code") == utils.REQUEST_CODES["CLOSE"]):
                    self.close_server(client_socket)
                
                if(data.get("code") == utils.REQUEST_CODES["PING"]):
                    self.ping(client_socket, interlaucutor)
                    
                if(data.get("code") == utils.REQUEST_CODES["DISCONNECT"]):
                    res = self.disconnect_client(client_socket, data, interlaucutor)
                    if res == 1:
                        break
                        
                if(data.get("code") == utils.REQUEST_CODES["FRIENDS_LIST"]):
                    self.get_friends_list(client_socket, data, interlaucutor)
                    
                if(data.get("code") == utils.REQUEST_CODES["SEND_TEXT"]):
                    self.send_text(client_socket, data, interlaucutor)
                    
                if(data.get("code") == utils.REQUEST_CODES["MESSAGES_RETRIEVE"]):
                    self.get_messages(client_socket, data['payload'], interlaucutor)
                    
        except Exception as e:
            print(f"An error occurred in client listener.\n(VoIPServerCLI) ")
            self.logger.error(f"An error occurred in client listener: {e.__traceback__.tb_lineno} {e}")

    def describe(self):
        return f"VoIpServer -- {self} --"
    
    def update_state(self, state):
        self.running = state

    def load_clients(self):
        self.clients = utils.get_all_clients_from_json()

    def is_client_available(self, id):
        return any(client['id'] == id for client in self.available_clients)

    def can_connect(self, id):
        if id in [client['id'] for client in self.clients]:
            return True
        return False
    
    def connect(self, id, client_socket: socket.socket, public_key=None):
        self.logger.info(f"Client {id} is trying to connect.")
        if self.can_connect(id):
            for client in self.available_clients:
                if client['id'] == id:
                    self.logger.info(f"Client {id} is already connected.")
                    return {"code": utils.REQUEST_CODES["OK"], "payload": f"You are already connected."}
            username = [client['username'] for client in self.clients if client['id'] == id]
            if username:
                username = username[0]
            else:
                username = "Unknown"
            self.available_clients.append({"id": id, "username": username, "socket": client_socket, "public_key": public_key})
            self.logger.info(f"Client {id} connected.")
            return {"code": utils.REQUEST_CODES["OK_CONNECT"], "payload": username, "public_key": self.public_key.decode('utf-8')}
        else:
            return {"code": utils.REQUEST_CODES["BAD_REQUEST"], "payload": f"Client {id} is not allowed"}
        
    def disconnect(self, id, client_socket: socket.socket):
        try:
            self.logger.info(f"Client {id} is trying to disconnect.")
            client_socket.close()
            self.available_clients = [client for client in self.available_clients if client['id'] != id]
            self.logger.info(f"Client {id} disconnected.")
            return {"code": utils.REQUEST_CODES["OK_DISCONNECT"], "payload": f"Client {id} disconnected successfully."}
        except socket.error as e:
            self.logger.error(f"Error while disconnecting: {e}")
            return {"code": utils.REQUEST_CODES["INTERNAL_ERROR"], "payload": f"Failed to disconnect client {id}."}

    def start(self):
        self.update_state(True)
        try:
            print(f"Starting server at {self.host}:{self.port}")
            print("(VoIPClientCLI) ")
            self.listen(5)
            self.logger.info(f"Server listening on {self.host}:{self.port}...")
            self.main_listenning_thread = threading.Thread(target=self._listen, daemon=True)
            self.main_listenning_thread.start()
            
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")

    def stop(self):
        self.update_state(False)