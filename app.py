'''
app.py contains all of the server application
this is where you'll find all of the get/post request handlers
the socket event handlers are inside of socket_routes.py
'''

from flask import Flask, render_template, request, abort, url_for, jsonify
from flask_socketio import SocketIO
from sqlalchemy.orm import Session
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

    if db.get_user(username) is None:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.insert_user(username, hashed_password)
        return url_for('home', username=username)
    return "Error: User already exists!"

# handler when a "404" error happens
@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.jinja'), 404

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


if __name__ == '__main__':

     socketio.run(app, host='localhost', port=5000, ssl_context=(cert_path, key_path))