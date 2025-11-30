import socket
import logging
import json
import threading

from voip.utils import REQUEST_CODES

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
            data = client_socket.recv(1024).decode('utf-8')
            data = json.loads(data)

            if(data.get("code") == REQUEST_CODES["CONNECT"]):
                response = self.connect(data['payload']['id'], client_socket)
                client_socket.send(json.dumps(response).encode('utf-8'))
                if response.get("code") == REQUEST_CODES["OK"]:
                    t = threading.Thread(target=self._listen_client, daemon=True, args=[client_socket,])
                    t.start()

        #self.logger.info(f"Server stopped at {datetime.datetime.now}")

    def _listen_client(self, client_socket: socket.socket):
        while True:
            data = client_socket.recv(1024).decode('utf-8')
            data = json.loads(data)

            if(data.get("code") == REQUEST_CODES["CLOSE"]):
                break
            if(data.get("code") == REQUEST_CODES["PING"]):
                client_socket.send(json.dumps({"code": REQUEST_CODES["OK"]}).encode('utf-8'))
            if(data.get("code") == REQUEST_CODES["DISCONNECT"]):
                client_socket.send(json.dumps({"code": REQUEST_CODES["OK"], "payload": f"Client {data['payload']['id']} disconnected."}).encode('utf-8'))
                print(f"Disconnecting client {data['payload']['id']}...")
                response = self.disconnect(data['payload']['id'], client_socket)
                if(response.get("code") == REQUEST_CODES["OK"]):
                    break
                else:
                    client_socket.send(json.dumps(response).encode('utf-8'))
            if(data.get("code") == REQUEST_CODES["FRIENDS_LIST"]):
                friends = [client['username'] for client in self.available_clients if client.get('id') != data['payload'].get('id')]
                if not friends:
                    friends = []
                client_socket.send(json.dumps({"code": REQUEST_CODES["OK"], "payload": friends}).encode('utf-8'))

    def describe(self):
        return f"VoIpServer -- {self} --"
    
    def update_state(self, state):
        self.running = state

    def load_clients(self):
        try:
            with open('voip/server/clients.json', 'r') as f:
                self.clients = json.load(f).get("clients", [])
        except FileNotFoundError:
            with open('voip/server/clients.json', 'w') as f:
                pass

    def is_client_available(self, id):
        return any(client['id'] == id for client in self.available_clients)

    def can_connect(self, id):
        if id in [client['id'] for client in self.clients]:
            return True
        return False
    
    def connect(self, id, client_socket: socket.socket):
        self.logger.info(f"Client {id} is trying to connect.")
        if self.can_connect(id):
            for client in self.available_clients:
                if client['id'] == id:
                    self.logger.info(f"Client {id} is already connected.")
                    return {"code": REQUEST_CODES["OK"], "payload": f"You are already connected."}
            username = [client['username'] for client in self.clients if client['id'] == id]
            if username:
                username = username[0]
            else:
                username = "Unknown"
            self.available_clients.append({"id": id, "username": username, "socket": client_socket})
            self.logger.info(f"Client {id} connected.")
            return {"code": REQUEST_CODES["OK"], "payload": username}
        else:
            return {"code": REQUEST_CODES["BAD_REQUEST"], "payload": f"Client {id} is not allowed"}
        
    def disconnect(self, id, client_socket: socket.socket):
        try:
            self.logger.info(f"Client {id} is trying to disconnect.")
            client_socket.close()
            self.available_clients = [client for client in self.available_clients if client['id'] != id]
            self.logger.info(f"Client {id} disconnected.")
            return {"code": REQUEST_CODES["OK"], "payload": f"Client {id} disconnected successfully."}
        except socket.error as e:
            self.logger.error(f"Error while disconnecting: {e}")
            return {"code": REQUEST_CODES["INTERNAL_ERROR"], "payload": f"Failed to disconnect client {id}."}

    def start(self):
        self.update_state(True)
        try:
            print(f"Starting server at {self.host}:{self.port}")
            self.listen(5)
            self.logger.info(f"Server listening on {self.host}:{self.port}...")
            self.main_listenning_thread = threading.Thread(target=self._listen, daemon=True)
            self.main_listenning_thread.start()
            
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")

    def stop(self):
        self.update_state(False)