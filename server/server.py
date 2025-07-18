import json
import socket
import threading
import logging

class VoIPServer(threading.Thread):
    def __init__(self, port=8080, host="127.0.0.1"):
        super().__init__()
        self.port = port
        self.host = host
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.running = True

        self.clients = []
        self.available_clients = []
        self.load_clients()

        self.logger = logging.getLogger("VoIPServer")
        self.logger.setLevel(logging.DEBUG)
        self.file_handler = logging.FileHandler("VoIPServer.log")
        self.file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.file_handler.setFormatter(formatter)
        self.logger.addHandler(self.file_handler)

    def load_clients(self):
        try:
            with open('server/clients.json', 'r') as f:
                self.clients = json.load(f).get("clients", [])
        except FileNotFoundError:
            self.clients = [{"id": 1, "socket": None}]

    def is_client_available(self, id):
        return any(client['id'] == id for client in self.available_clients)

    def can_connect(self, id):
        with open('server/clients.json', 'r') as f:
            file_content = json.load(f)
        clients = file_content.get("clients", [])
        if id in [client['id'] for client in clients]:
            return True
        return False
    
    def connect(self, id, client_socket):
        if self.is_client_available(id):
            for client in self.available_clients:
                if client['id'] == id:
                    return {"status": "OK", "message": f"Client {id} is already connected."}
        else:
            if self.can_connect(id):
                self.available_clients.append({"id": id, "socket": client_socket})
                return {"status": "OK", "message": f"Welcome back, {id}!"}
            return {"status": "ERROR", "message": f"Client {id} is not allowed"}
        
    def disconnect(self, id, client_socket):
        try:
            client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
            client_socket.close()
            self.available_clients = [client for client in self.available_clients if client['id'] != id]
            return {"status": "OK", "message": f"Client {id} is disconnected."}
        except socket.error as e:
            self.logger.error(f"Error while disconnecting: {e}")
            return {"status": "ERROR", "message": f"Failed to disconnect client {id}."}

    def stop(self):
        self.available_clients = []
        self.running = False
        self.server_socket.close()
        self.logger.info("Server stopped.")

    def run(self):
        try:
            self.server_socket.listen(5)
            self.logger.info(f"Server listening on {self.host}:{self.port}...")
            while self.running:
                client_socket, addr = self.server_socket.accept()
                data = client_socket.recv(1024).decode('utf-8')
                data = json.loads(data)

                self.logger.info(data)

                if data.get("type") == "connect":
                    self.logger.info(f"Connection from {addr}")
                    client_id = data["payload"]["id"]
                    response = self.connect(client_id, client_socket)
                    if response.get("status") == "ERROR":
                        self.logger.error(f"Connection failed for client {client_id}")
                    else:
                        self.logger.info(f"Connection successful for client {client_id}")
                    client_socket.send(response.get("message").encode('utf-8'))
                elif data.get("type") == "disconnect":
                    self.logger.info(f"Disconnection request from {addr}")
                    client_id = data["payload"]["id"]
                    response = self.disconnect(client_id, client_socket)
                    if response.get("status") == "ERROR":
                        self.logger.error(f"Disconnection failed for client {client_id}")
                    else:
                        self.logger.info(f"Disconnection successful for client {client_id}")
                else:
                    self.logger.info(data["payload"])
                    client_socket.send("Message received successfully".encode('utf-8'))
        except threading.ThreadError as e:
            pass
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")