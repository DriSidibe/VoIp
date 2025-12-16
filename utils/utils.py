import datetime
import json
import os
import socket

from . import security

UNIT_CHUNK_SIZE = 1024
DELIMITER = b'::END::'
CLIENT_STATUS_PING_TIME = 10  # in seconds
CLIENT_STATUS_CHECK_TIME = 10  # in seconds
CLIENT_STATUS_CHECK_TIMELAPSE = 1000
CALL_NOTIFICATION_DELAY = 2

RINGTONE = "ringtone.wav"

REQUEST_CODES = {
    "OK": 200,
    "OK_CONNECT": 201,
    "OK_DISCONNECT": 202,
    "BAD_REQUEST": 400,
    "NOT_FOUND": 404,
    "INTERNAL_ERROR": 500,
    "CLOSE": 600,
    "PING": 700,
    "SERVER_PING": 701,
    "CONNECT": 800,
    "DISCONNECT": 900,
    "FRIENDS_LIST": 1000,
    "SEND_TEXT": 1100,
    "NOT_FOUND": 1200,
    "MESSAGES_RETRIEVE": 1300,
    "DESCRIBE": 1400,
    "SERVER_START": 1500,
    "SERVER_STOP": 1600,
    "VOICECALL_REQUEST": 1700
}

isRinging = False

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

def ring(username):
    global isRinging
    import pygame

    pygame.mixer.init()
    pygame.mixer.music.load(RINGTONE)

    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pass
    print(" ## RINGING ## {username} is calling you !")
    isRinging = False


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
        print("(VoIPClientCLI) ", end='', flush=True)
    else:
        print("No friends available on the server.")
        
def store_message(sender, recipient, datetime, message):
    file_path = os.path.join(base_dir, '..', 'messages.json')
    try:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump({}, f, indent=4)
        with open(file_path, 'r') as f:
            data = json.load(f)
        sender_messages = data.get(sender, [])
        sender_messages.append({
            "to": recipient,
            "datetime": datetime,
            "message": message
        })
        recipient_messages = data.get(recipient, [])
        recipient_messages.append({
            "from": sender,
            "datetime": datetime,
            "message": message
        })
        data[sender] = sender_messages
        data[recipient] = recipient_messages
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error storing message: {e}")

def connection_required(isConnected):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                if isConnected():
                    func(*args, **kwargs)
                else:
                    print("Client is not connected to the server.")
            except socket.error as e:
                print(f"Server not available: {e}")
        return wrapper
    return decorator

def get_messages(interlocutor, from_date=None, to_date=None, from_user=None):
        file_path = base_dir + '/../messages.json'
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            user_messages = data.get(interlocutor.get("username", "no username"), [])
            filtered_messages = []
            for msg in user_messages:
                msg_datetime = datetime.datetime.fromisoformat(msg['datetime'].replace("Z", "+00:00"))
                if from_date and msg_datetime < from_date:
                    continue
                if to_date and msg_datetime > to_date:
                    continue
                if from_user and msg.get('from', '') != from_user and msg.get('to', '') != from_user:
                    continue
                filtered_messages.append(msg)
                autor_ = ""
                try:
                    autor_ = msg['from']
                    msg['autor'] = autor_ + '->me'
                except KeyError:
                    autor_ = msg['to']
                    msg['autor'] = 'me->' + autor_
                finally:
                    autor_ = str(msg["autor"]).replace(interlocutor.get("username", "no username"), "me")
                    msg['autor'] = autor_
            return filtered_messages
        except FileNotFoundError:
            print("No messages found.")
            return []
        except Exception as e:
            print(f"Error retrieving messages: {e.__traceback__.tb_lineno} {e}")
            return []
        
def print_client_logs_on_terminal(request_code, messages=None):
    if request_code == REQUEST_CODES["OK_CONNECT"]:
        print(f"Connected to server as {messages}.")
            
def print_server_logs_on_terminal(request_code, messages=None):
    print("\n>> ", end='')
    if request_code == REQUEST_CODES["DISCONNECT"]:
        print(f"Disconnecting client {messages}...")
    elif request_code == REQUEST_CODES["INTERNAL_ERROR"]:
        print(f"An error occurred in client listener.")
    elif request_code == REQUEST_CODES["DESCRIBE"]:
        print(f"VoIpServer -- {messages} --")
    elif request_code == REQUEST_CODES["SERVER_START"]:
        print(f"{messages}")
    elif request_code == REQUEST_CODES["SERVER_STOP"]:
        print(f"Stopping server...")

def print_logs_on_terminal(request_code, interlocutor="client", messages=None):
    if interlocutor == "client":
        print_client_logs_on_terminal(request_code, messages)
    else:
        print_server_logs_on_terminal(request_code, messages)
        
def encode_message(message: dict):
    return json.dumps(message).encode('utf-8')
        
def send_message(message: bytes, _socket: socket.socket, public_key = None):
    try:
        message = security.encrypt_message(message, public_key.encode('utf-8')) if public_key else message
        if public_key:
            for key in message:
                message[key] = message[key].hex()
            message = encode_message(message)
        message += DELIMITER
        return _socket.sendall(message)
    except socket.error as e:
        raise e
    
def receive_message(_socket: socket.socket, private_key = None):
    try:
        response = b''
        while response.endswith(DELIMITER) is False:
            response += _socket.recv(UNIT_CHUNK_SIZE)
        response = response[:-len(DELIMITER)]
        if private_key:
            response = response.decode('utf-8')
            response = json.loads(response)
            for key in response.copy():
                response[key] = bytes.fromhex(response[key])
        message = security.decrypt_message(response, private_key) if private_key else response
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