'''
socket_routes
file containing all the routes related to socket.io
'''


from flask_socketio import join_room, emit, leave_room
from flask import request

try:
    from __main__ import socketio
except ImportError:
    from app import socketio

from models import Room, User

import db, os, json, datetime

room = Room()

# when the client connects to a socket
# this event is emitted when the io() function is called in JS
@socketio.on('connect')
def connect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    if db.is_user_muted(username):
        emit('error', {'message': 'You are muted and cannot join the room'})
        return
    if room_id is None or username is None:
        return
    # socket automatically leaves a room on client disconnect
    # so on client connect, the room needs to be rejoined
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

@socketio.on("send")
def send(sender, receiver, message,encryptedMessage_sender,signature,room_id):
    # send the message
    emit("incoming_message", (f"{sender}: {message}: {signature}"),to=room_id, include_self=False)
    
    # save file 
    file_path_sender = f"messages/{sender}/{receiver}.json"
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
    data_sender.append({"username": sender, "message": encryptedMessage_sender,"signature": signature,"timestamp": str(datetime.datetime.now())})
    data_receiver.append({"username": sender, "message": message,"signature": signature, "timestamp": str(datetime.datetime.now())})

    # save the messages
    with open(file_path_sender, "w") as file:
        json.dump(data_sender, file, indent=4)
    with open(file_path_receiver, "w") as file:
        json.dump(data_receiver, file, indent=4)

    
# join room event handler
# sent when the user joins a room
@socketio.on("join")
def join(sender_name, receiver_name):
    if sender_name == receiver_name:
        return "You can't chat with yourself :("
    
    receiver = db.get_user(receiver_name)
    if receiver is None:
        return "Unknown receiver!"
    
    sender = db.get_user(sender_name)
    if sender is None:
        return "Unknown sender!"

    room_id = room.get_room_id(receiver_name)

    # if the user is already inside of a room 
    if room_id is not None:
        # check if the user is friend for all the users in the chat room
        for user in room.get_users(room_id):
            if sender_name not in db.get_friends_list(user) and user != sender_name:
                return "You can only chat with friends!"
        
        room.join_room(sender_name, room_id)
        join_room(room_id)
        # emit to everyone in the room except the sender
        emit("incoming", (f"{sender_name} has joined the room.", "green"), to=room_id, include_self=False)
        # emit only to the sender
        emit("incoming", (f"{sender_name} has joined the room. Now talking to everyone in the room.", "green"))
        socketio.emit('update_room_users', list(room.get_users(room_id)), room=room_id)
        return json.dumps({"room": room_id, "users": room.get_users(room_id)})


    # if the user isn't inside of any room, 
    # perhaps this user has recently left a room
    # or is simply a new user looking to chat with someone
    room_id = room.create_room(sender_name, receiver_name)
    join_room(room_id)
    emit("incoming", (f"{sender_name} has joined the room. Now talking to everyone in the room.", "green"), to=room_id)
    socketio.emit('update_room_users', list(room.get_users(room_id)), room=room_id)
    return json.dumps({"room": room_id, "users": room.get_users(room_id)})

# leave room event handler
@socketio.on("leave")
def leave(username, room_id):
    emit("incoming", (f"{username} has left the room.", "red"), to=room_id)
    leave_room(room_id)
    room.leave_room(username)



