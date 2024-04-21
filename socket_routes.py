'''
socket_routes
file containing all the routes related to socket.io
'''


from flask_socketio import join_room, emit, leave_room
from flask import request
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.fernet import Fernet
from base64 import urlsafe_b64encode
import os,json,datetime

try:
    from __main__ import socketio
except ImportError:
    from app import socketio

from models import Room

import db

room = Room()

def derive_key(password, salt, length=32):
    # Derive a cryptographic key from a password
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

# when the client connects to a socket
# this event is emitted when the io() function is called in JS
@socketio.on('connect')
def connect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    leave_room(room_id)
    room.leave_room(username)

# event when client disconnects
# quite unreliable use sparingly
@socketio.on('disconnect')
def disconnect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    if room_id is None or username is None:
        return
    emit("incoming", (f"{username} has disconnected and left", "red"), to=int(room_id))
    leave_room(room_id)
    room.leave_room(username)

def encrypt_data(key, data):
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode())  
    return encrypted_data

@socketio.on("send")
def send(username, message,encryptedMessage_sender,hmac, room_id):
    users = room.get_users(room_id)
    if username == users[0]:
        sender = users[0]
        receiver = users[1]
    else:
        sender = users[1]
        receiver = users[0]
    # send the message
    emit("incoming_message", (f"{username}: {message}"),hmac,to=room_id)
    
    # save file 
    file_path_sender = f"messages/{username}/{receiver}.json"
    file_path_receiver = f"messages/{receiver}/{sender}.json"
    
    # create the directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path_sender), exist_ok=True)
    os.makedirs(os.path.dirname(file_path_receiver), exist_ok=True)
    
    # load the existing messages
    if os.path.exists(file_path_sender):
        with open(file_path_sender, "r") as file:
            data_sender = json.load(file)
    else:
        data_sender = []
    if os.path.exists(file_path_receiver):
        with open(file_path_receiver, "r") as file:
            data_receiver = json.load(file)
    else:
        data_receiver = []

    # append the new message
    data_sender.append({"username": username, "message": encryptedMessage_sender, "timestamp": str(datetime.datetime.now())})
    data_receiver.append({"username": username, "message": message, "timestamp": str(datetime.datetime.now())})

    # save the messages
    with open(file_path_sender, "w") as file:
        json.dump(data_sender, file, indent=4)
    with open(file_path_receiver, "w") as file:
        json.dump(data_receiver, file, indent=4)

    
# join room event handler
# sent when the user joins a room
@socketio.on("join")
def join(sender_name, receiver_name):
    receiver = db.get_user(receiver_name)
    if receiver is None:
        return "Unknown receiver!"
    
    sender = db.get_user(sender_name)
    if sender is None:
        return "Unknown sender!"

    room_id = room.get_room_id(receiver_name)
    print(f"Room ID: {room_id}")

    # if the user is already inside of a room 
    if room_id is not None:
        room.join_room(sender_name, room_id)
        join_room(room_id)
        print("Need to HMAC initialize")
        # emit to everyone in the room except the sender
        emit("incoming", (f"{sender_name} has joined the room.", "green"), to=room_id, include_self=False)
        # emit only to the sender
        emit("incoming", (f"{sender_name} has joined the room. Now talking to {receiver_name}.", "green"))
        emit("HMAC initialize")
        return room_id

    # if the user isn't inside of any room, 
    # perhaps this user has recently left a room
    # or is simply a new user looking to chat with someone
    room_id = room.create_room(sender_name, receiver_name)
    join_room(room_id)
    emit("incoming", (f"{sender_name} has joined the room. Now talking to {receiver_name}.", "green"), to=room_id)
    return room_id

# leave room event handler
@socketio.on("leave")
def leave(username, room_id):
    emit("incoming", (f"{username} has left the room.", "red"), to=room_id)
    leave_room(room_id)
    room.leave_room(username)

# event handler for hmac 
@socketio.on("HMAC_key")
def hmac_key(hmac_key, room_id):
    emit("HMACkey_incoming", hmac_key, to=room_id,include_self=False)
