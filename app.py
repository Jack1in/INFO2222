'''
app.py contains all of the server application
this is where you'll find all of the get/post request handlers
the socket event handlers are inside of socket_routes.py
'''

from flask import Flask, render_template, request, abort, url_for, jsonify,send_from_directory,session,redirect
import os
from flask_socketio import SocketIO
from sqlalchemy.orm import Session
from datetime import timedelta
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
app.config['SSL_CERT_PATH'] = cert_path
app.config['SSL_KEY_PATH'] = key_path
# secret key used to sign the session cookie
app.config['SECRET_KEY'] = 'nice_secret_ley'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SERVER_NAME'] = 'localhost:5000'
app.config['PREFERRED_URL_SCHEME'] = 'https'
with open('config.json', 'r') as json_file:
    config = json.load(json_file)
    app.config['ADMIN_CODE_HASH'] = config['admin_code_hash']
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
        session_key = secrets.token_hex()
        session[username] = session_key
        db.set_online_status(username, True)
        
        print(f"User Role: {user.role}, Online Status: {user.online_status}")
        
        home_url = url_for('home', username=request.json.get("username"), sessionKey=session_key)
        return jsonify({"home_url": home_url, "session_key": session_key}), 200
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
    # alwasy convert to text to avoid xss attacks
    username = request.json.get("username")
    password = request.json.get("password")
    publicKey = request.json.get("publicKey")
    adminCode = request.json.get("adminCode")
    
    # Check if the user already exists
    if db.get_user(username) is None:
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Determine role based on admin code
        if adminCode and bcrypt.checkpw(adminCode.encode('utf-8'), app.config['ADMIN_CODE_HASH'].encode('utf-8')):
            role = 'admin'
        else:
            role = 'user'
        
        # Insert the user with the determined role
        db.insert_user(username, hashed_password, publicKey, role)
        return url_for('login')
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

@app.route("/request_history", methods=["POST"])
def request_history():
    try:
        data = request.get_json()
        username = data.get("username")
        chat_partner = data.get("chatPartner")
        sessionKey = data.get("sessionKey")
        user = db.get_user(username)
        if user is None:
            return jsonify({"error": "User not found"}), 404
        if sessionKey != session.get(username):
            return "invalid session key", 404
        messages = get_messages(username, chat_partner)
        return messages
    except Exception as e:
        print(e)
        return jsonify({"error": "An error occurred"}), 500

def get_messages(username, chat_partner):
    directory = os.path.join(app.root_path, 'messages', username)
    filename = f'{chat_partner}.json'
    # check if the file exists
    if not os.path.exists(os.path.join(directory, filename)):
        return jsonify([])
    return send_from_directory(directory, filename)


# home page, where the messaging app is
@app.route("/home")
def home():
    username = request.args.get("username")
    sessionKey = request.args.get('sessionKey')
    if request.args.get("sessionKey") != session.get(username):
        return redirect(url_for("login"))
    friend_requests = db.get_friend_requests(username)
    friends_list = db.get_friends_list(username)
    return render_template("home.jinja", username=username, friend_requests=friend_requests, friends_list=friends_list,sessionKey=sessionKey)

@app.route("/send_request", methods=["POST"])
def send_request():
    if not request.is_json:
        abort(400)  # Bad request
    sessionKey = request.json.get("sessionKey")
    sender = request.json.get("sender")
    if sessionKey != session.get(sender):
        return "invalid session key"
    receiver = request.json.get("receiver")
    if sender == receiver:
        return jsonify({"result": "You can't send a friend request to yourself!"})
    result = db.send_friend_request(sender, receiver)
    return jsonify({"result": result})


# Handles accepting friend requests
@app.route("/accept_friend_request", methods=["POST"])
def accept_friend_request():
    if not request.is_json:
        abort(400)  # Bad request
    sender = request.json.get("sender")
    receiver = request.json.get("receiver")
    sessionKey = request.json.get("sessionKey")
    if sessionKey != session.get(receiver):
        return jsonify("invalid session key")
    result = db.accept_friend_request(sender, receiver)
    return jsonify({"result": result})

# Handles rejecting friend requests
@app.route("/reject_friend_request", methods=["POST"])
def reject_friend_request():
    if not request.is_json:
        abort(400)  # Bad request
    sender = request.json.get("sender")
    receiver = request.json.get("receiver")
    sessionKey = request.json.get("sessionKey")
    if sessionKey != session.get(receiver):
        return jsonify("invalid session key")
    result = db.reject_friend_request(sender, receiver)
    return jsonify({"result": result})

@app.route("/remove_friend", methods=["POST"])
def remove_friend():
    if not request.is_json:
        abort(400)
    username = request.json.get("username")
    friend_username = request.json.get("friend_username")
    sessionKey = request.json.get("sessionKey")
    if sessionKey != session.get(username):
        return jsonify("invalid session key")
    result = db.remove_friend(username, friend_username)
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
    
@app.route('/logout', methods=['POST'])
def logout():
    if not request.is_json:
        abort(400)
    username = request.json.get("username")
    user =  db.get_user(username)
    session.pop(username)
    db.set_online_status(username, False)
    print(f"User Role: {user.role}, Online Status: {user.online_status}")
    return "logged out"

@app.route('/knowledge_repository')
def knowledge_repository():
    username = request.args.get('username')
    sessionKey = request.args.get('sessionKey')
    print(f"Knowledge Repository - Username: {username}, Session Key: {sessionKey}")
    return render_template('knowledge_repository.jinja', username=username, sessionKey=sessionKey)

@app.route('/post_article', methods=['POST'])
def post_article():
    try:
        if not request.is_json:
            print("Request does not contain JSON")
            return jsonify({"error": "Request does not contain JSON"}), 400
        
        data = request.get_json()
        
        print("Received data:", data)
        
        username = data.get('username')
        session_key = data.get('sessionKey')
        content = data.get('content')

        # Validate session key
        if session.get(username) != session_key:
            return jsonify({"error": "Invalid session key"}), 403

        article = {
            "username": username,
            "content": content,
        }

        # Ensure articles.json exists and append the new article
        if not os.path.exists('articles.json'):
            with open('articles.json', 'w') as file:
                json.dump([], file)

        with open('articles.json', 'r+') as file:
            articles = json.load(file)
            articles.append(article)
            file.seek(0)
            json.dump(articles, file, indent=4)

        return jsonify({"message": "Article posted successfully"}), 200
    except Exception as e:
        # Print error message to the console
        print(f"Error occurred: {e}")
        # Return a 500 error and the error message
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, host='localhost', port=5000, ssl_context=(cert_path, key_path))
    
