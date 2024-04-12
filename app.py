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
# import logging

# this turns off Flask Logging, uncomment this to turn off Logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

app = Flask(__name__)

# secret key used to sign the session cookie
app.config['SECRET_KEY'] = secrets.token_hex()
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
    if request.args.get("username") is None:
        abort(404)
    return render_template("home.jinja", username=request.args.get("username"))


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
        user1.add_friend('user2', session)
        # return the users
        return jsonify({
            "User1": user1_info.username,
            "User2": user2_info.username,
            "User1 Friends": [friend.username for friend in user1_info.friends]
        })


if __name__ == '__main__':

    socketio.run(app)
