import json
import os
import socket

from . import security

REQUEST_CODES = {
    "OK": 200,
    "BAD_REQUEST": 400,
    "NOT_FOUND": 404,
    "INTERNAL_ERROR": 500,
    "CLOSE": 600,
    "PING": 700,
    "CONNECT": 800,
    "DISCONNECT": 900,
    "FRIENDS_LIST": 1000,
    "SEND_TEXT": 1100
}

base_dir = os.path.dirname(os.path.abspath(__file__))

def get_all_clients_from_json():
    file_path = os.path.join(base_dir, '..', 'clients.json')
    import json
    try:
        with open(file_path, 'r') as f:
            clients = json.load(f).get("clients", [])
            return clients
    except FileNotFoundError:
        return {}
    
    
def get_all_settings_from_json():
    file_path = os.path.join(base_dir, '..', 'settings.json')
    import json
    try:
        with open(file_path, 'r') as f:
            settings = json.load(f)
            return settings
    except FileNotFoundError:
        return {}
    
def get_client_by_id(clients, id):
    for client in clients:
        if client['id'] == id:
            return client
    return None

def get_client_by_username(clients, username):
    for client in clients:
        if client['username'] == username:
            return client
    return None

def update_client(client):
    clients = get_all_clients_from_json()
    for i, c in enumerate(clients):
        if c['id'] == client['id']:
            clients[i] = client
            break
    else:
        clients.append(client)
    with open('voip/server/clients.json', 'w') as f:
        json.dump({"clients": clients}, f, indent=4)
        
def print_friends(friends):
    if friends:
        print("Available friends on the server:")
        for friend in friends:
            print(f"- {friend}")
    else:
        print("No friends available on the server.")
        
def encode_message(message: dict):
    return json.dumps(message).encode('utf-8')
        
def send_message(message, _socket: socket.socket, public_key = None):
    try:
        message = security.encrypt_message(message, public_key.encode('utf-8')) if public_key else message
        return _socket.send(message)
    except socket.error as e:
        raise e
    
def receive_message(_socket: socket.socket, private_key = None):
    try:
        response = _socket.recv(1024)
        response = security.decrypt_message(response, private_key) if private_key else response
        message = response.decode('utf-8')
        return message
    except socket.error as e:
        raise e
        
def send_message_and_wait_for_response(message, _socket: socket.socket, private_key=None, public_key=None):
    try:
        send_message(message, _socket, public_key)
        message = receive_message(_socket, private_key)
        return message
    except socket.error as e:
        raise e