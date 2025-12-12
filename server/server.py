import socket
import logging
import json
import threading
import time

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
        self.available_clients = {}
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
        
        self.available_client_lock = threading.Lock()
        
        threading.Thread(target=self.ping_clients, daemon=True).start()

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
        utils.print_logs_on_terminal(utils.REQUEST_CODES["DISCONNECT"], "server", data['payload']['id'])
        response = self.disconnect(data['payload']['id'], client_socket)
        if(response.get("code") == utils.REQUEST_CODES["OK"]):
            return 1
        else:
            utils.send_message(utils.encode_message(response), client_socket, interlaucutor.get("public_key", None))
        return -1
                
    def ping_client(self, client_id, client_socket, public_key):
        try:
            utils.send_message(utils.encode_message({"code": utils.REQUEST_CODES["SERVER_PING"]}), client_socket, public_key)
        except:
            with self.available_client_lock:
                del self.available_clients[client_id]
    
    def ping_clients(self):
        while True:
            while self.running:
                for client_id, client in self.available_clients.copy().items():
                    try:
                        with self.available_client_lock:
                            self.available_clients[client_id]["ping_start"] = time.time()
                        threading.Thread(target=self.ping_client, daemon=True, args=[client_id, client['socket'], client.get("public_key", None),]).start()
                    except socket.error as e:
                        self.logger.error(f"Error in ping_clients: {e}")
                time.sleep(utils.CLIENT_STATUS_PING_TIME)
    
    def is_client_connected(self, username: str):
        for client_id, client in self.available_clients.items():
            if client['username'] == username:
                return True
        return False
    
    def get_friends_list(self, data):
        friends = [client['username'] for client_id, client in self.available_clients.items() if client.get('id') != data['payload'].get('id')]
        if not friends:
            friends = []
        return friends
    
    def get_all_friends(self, client_socket: socket.socket, data, interlaucutor: dict):
        all_friends = [client['username'] + " ✔" if self.is_client_connected(client['username']) else client['username'] for client in self.clients if client.get('id') != data['payload'].get('id')]
        if not all_friends:
            all_friends = []
        message = {
            "code": utils.REQUEST_CODES["FRIENDS_LIST"],
            "payload": all_friends,
        }
        utils.send_message(utils.encode_message(message), client_socket, interlaucutor.get("public_key", None))
        
    def send_text(self, client_socket: socket.socket, data, interlaucutor: dict):
        recipient_username = data['payload'].get('to')
        message_text = data['payload'].get('message')
        _datetime = data['payload'].get('datetime')
        sender_username = data['payload'].get('from', 'Unknown')
        recipient_client = None

        for client_id, client in self.available_clients.items():
            if client['username'] == recipient_username:
                recipient_client = client
                break
        if not recipient_client:
            for client in self.clients:
                if client['username'] == recipient_username:
                    recipient_client = client
                    break

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
            
            if recipient_client.get('socket'):
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
                
                data["payload"] = data.get("payload", {'id': None})
                
                interlaucutor = self.available_clients.get(data['payload'].get('id'), {})
                

                if(data.get("code") == utils.REQUEST_CODES["CLOSE"]):
                    self.close_server(client_socket)
                
                elif(data.get("code") == utils.REQUEST_CODES["PING"]):
                    self.ping(client_socket, interlaucutor)
                    
                elif(data.get("code") == utils.REQUEST_CODES["DISCONNECT"]):
                    res = self.disconnect_client(client_socket, data, interlaucutor)
                    if res == 1:
                        break
                        
                elif(data.get("code") == utils.REQUEST_CODES["FRIENDS_LIST"]):
                    self.get_all_friends(client_socket, data, interlaucutor)
                    
                elif(data.get("code") == utils.REQUEST_CODES["SEND_TEXT"]):
                    self.send_text(client_socket, data, interlaucutor)
                    
                elif(data.get("code") == utils.REQUEST_CODES["MESSAGES_RETRIEVE"]):
                    self.get_messages(client_socket, data['payload'], interlaucutor)
                    
        except socket.error as e:
            pass
        except Exception as e:
            utils.print_logs_on_terminal(utils.REQUEST_CODES["INTERNAL_ERROR"], "server")
            self.logger.error(f"An error occurred in client listener: {e.__traceback__.tb_lineno} {e}")
            exit()

    def describe(self):
        utils.print_logs_on_terminal(utils.REQUEST_CODES["DESCRIBE"], "server", self)
    
    def update_state(self, state):
        self.running = state

    def load_clients(self):
        self.clients = utils.get_all_clients_from_json()

    def is_client_available(self, id):
        return any(client['id'] == id for client_id, client in self.available_clients.items())

    def can_connect(self, id):
        if id in [client['id'] for client in self.clients]:
            return True
        return False
    
    def connect(self, id, client_socket: socket.socket, public_key=None):
        self.logger.info(f"Client {id} is trying to connect.")
        if self.can_connect(id):
            for client_id, client in self.available_clients.items():
                if client['id'] == id:
                    self.logger.info(f"Client {id} is already connected.")
                    return {"code": utils.REQUEST_CODES["OK"], "payload": f"You are already connected."}
            username = [client['username'] for client in self.clients if client['id'] == id]
            if username:
                username = username[0]
            else:
                username = "Unknown"
            with self.available_client_lock:
                self.available_clients[id] = {"id": id, "username": username, "socket": client_socket, "public_key": public_key, "ping_start": None, "ping_end": None}
            self.logger.info(f"Client {id} connected.")
            return {"code": utils.REQUEST_CODES["OK_CONNECT"], "payload": username, "public_key": self.public_key.decode('utf-8')}
        else:
            return {"code": utils.REQUEST_CODES["BAD_REQUEST"], "payload": f"Client {id} is not allowed"}
        
    def disconnect(self, id, client_socket: socket.socket):
        try:
            self.logger.info(f"Client {id} is trying to disconnect.")
            client_socket.close()
            with self.available_client_lock:
                del self.available_clients[id]
            self.logger.info(f"Client {id} disconnected.")
            return {"code": utils.REQUEST_CODES["OK_DISCONNECT"], "payload": f"Client {id} disconnected successfully."}
        except socket.error as e:
            self.logger.error(f"Error while disconnecting: {e}")
            return {"code": utils.REQUEST_CODES["INTERNAL_ERROR"], "payload": f"Failed to disconnect client {id}."}

    def start(self):
        self.update_state(True)
        try:
            self.listen(5)
            self.logger.info(f"Server listening on {self.host}:{self.port}...")
            self.main_listenning_thread = threading.Thread(target=self._listen, daemon=True)
            self.main_listenning_thread.start()
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")

    def stop(self):
        self.update_state(False)
        utils.print_logs_on_terminal(utils.REQUEST_CODES["SERVER_STOP"], "server")
        self.logger.info("Stopping server...")
        for client_id, client in self.available_clients.items():
            try:
                client['socket'].close()
            except socket.error as e:
                self.logger.error(f"Error while closing client socket: {e}")
        with self.available_client_lock:
            self.available_clients = {}
        try:
            self.close()
            self.logger.info("Server stopped.")
        except socket.error as e:
            self.logger.error(f"Error while stopping server: {e}")