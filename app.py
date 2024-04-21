'''
app.py contains all of the server application
this is where you'll find all of the get/post request handlers
the socket event handlers are inside of socket_routes.py
'''

from flask import Flask, render_template, request, abort, url_for, jsonify,send_from_directory
import os
from flask_socketio import SocketIO
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import json
from models import User, Room
import db
import secrets
import bcrypt
from flask import Flask, render_template
from flask_socketio import SocketIO
import os
# import logging

# this turns off Flask Logging, uncomment this to turn off Logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

app = Flask(__name__)
cert_dir = os.path.join(os.path.dirname(__file__), 'certs')
cert_path = os.path.join(cert_dir, 'localhost.crt')
key_path = os.path.join(cert_dir, 'localhost.key')
# secret key used to sign the session cookie
app.config['SECRET_KEY'] = secrets.token_hex()
app.config['SERVER_NAME'] = 'localhost:5000' 
app.config['PREFERRED_URL_SCHEME'] = 'https' 
app.config['SSL_CERT_PATH'] = cert_path
app.config['SSL_KEY_PATH'] = key_path
socketio = SocketIO(app)

# don't remove this!!
import socket_routes

# generate a key pair
def generate_key_pair(password: str):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    # use the password to encrypt the private key
    pem_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
    )
    # generate the public key
    pem_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem_private_key, pem_public_key

# index page
@app.route("/")
def index():
    return render_template("index.jinja")

# login page
@app.route("/login")
def login():    
    return render_template("login.jinja")

# handles a post request when the user clicks the log in button
@app.route("/login/user", methods=["POST"])
def login_user():
    if not request.is_json:
        abort(404)

    username = request.json.get("username")
    password = request.json.get("password")

    user =  db.get_user(username)
    if user is None:
        return "Error: User does not exist!"
    if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return url_for('home', username=request.json.get("username"))
    else:
        return "Error: Password does not match!"
    

# handles a get request to the signup page
@app.route("/signup")
def signup():
    return render_template("signup.jinja")

# handles a post request when the user clicks the signup button
@app.route("/signup/user", methods=["POST"])
def signup_user():
    if not request.is_json:
        abort(404)
    username = request.json.get("username")
    password = request.json.get("password")
    public_key = request.json.get("publicKey")
    
    if db.get_user(username) is None:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.insert_user(username, hashed_password,public_key)
        return url_for('home', username=username)
    return "Error: User already exists!"

@app.route('/api/public-keys/<username>', methods=['GET'])
def get_public_key(username):
    public_key = retrieve_public_key_for_user(username)
    if public_key:
        return jsonify({'publicKey': public_key}), 200
    else:
        return jsonify({'error': 'Public key not found'}), 404

def retrieve_public_key_for_user(username):
    user = db.get_user(username)
    if user:
        return user.public_key
    else:
        return None

# handler when a "404" error happens
@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.jinja'), 404

@app.route('/messages/<username>/<chatPartner>.json')
def get_messages(username, chatPartner):
    directory = os.path.join(app.root_path, 'messages', username)
    filename = f'{chatPartner}.json'

    try:
        return send_from_directory(directory, filename)
    except FileNotFoundError:
        abort(404, description="Resource not found")

# home page, where the messaging app is
@app.route("/home")
def home():
    username = request.args.get("username")
    if not username:
        abort(404)
    friend_requests = db.get_friend_requests(username)
    friends_list = db.get_friends_list(username)
    print("Data passed to template - Friend Requests:", friend_requests)  # Debugging line
    return render_template("home.jinja", username=username, friend_requests=friend_requests, friends_list=friends_list)

@app.route("/send_request", methods=["POST"])
def send_request():
    if not request.is_json:
        abort(400)  # Bad request
    sender = request.json.get("sender")
    receiver = request.json.get("receiver")
    result = db.send_friend_request(sender, receiver)
    return jsonify({"result": result})


# Handles accepting friend requests
@app.route("/accept_friend_request", methods=["POST"])
def accept_friend_request():
    if not request.is_json:
        abort(400)  # Bad request
    sender = request.json.get("sender")
    receiver = request.json.get("receiver")
    result = db.accept_friend_request(sender, receiver)
    return jsonify({"result": result})

# Handles rejecting friend requests
@app.route("/reject_friend_request", methods=["POST"])
def reject_friend_request():
    if not request.is_json:
        abort(400)  # Bad request
    sender = request.json.get("sender")
    receiver = request.json.get("receiver")
    result = db.reject_friend_request(sender, receiver)
    return jsonify({"result": result})


# test models
@app.route('/test')
def test_models():
    with Session(db.engine) as session:
        session.query(User).delete()
        session.commit()
        # create users
        user1 = User(username='user1', password='123456')
        user2 = User(username='user2', password='123456')
        session.add(user1)
        session.add(user2)
        session.commit()
        user1_info = session.query(User).filter_by(username='user1').first()
        user2_info = session.query(User).filter_by(username='user2').first()
        # add friends
        result = user1.send_request('user2', session)
        before_handle_user1_sent = user1.view_requests('sent')
        before_handle_user2_received = user2.view_requests('received')

        # reject the request
        user2.reject_request('user1', session)
        after_reject_user1_sent = user1.view_requests('sent')
        after_reject_user2_received = user2.view_requests('received')
        # send again
        user1.send_request('user2', session)
        # accept the request
        result_accept = user2.accept_request('user1', session)
        session.commit()
        after_accept_user1_friends = [friend.username for friend in user1.added_friends]
        after_accept_user2_friends = [friend.username for friend in user2.friends]
        # return the users
        return jsonify({
            "User1": user1_info.username,
            "User2": user2_info.username,
            "Before handle User1 Sent": before_handle_user1_sent,
            "Before handle User2 Received": before_handle_user2_received,
            "After Reject User1 Sent": after_reject_user1_sent,
            "After Reject User2 Received": after_reject_user2_received,
            "After Accept User1 Friends": after_accept_user1_friends,
            "After Accept User2 Friends": after_accept_user2_friends,
            "result from sending request": result,
            "result from accepting request": result_accept
        })


if __name__ == '__main__':

     socketio.run(app, host='localhost', port=5000, ssl_context=(cert_path, key_path))