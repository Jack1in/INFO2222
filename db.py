'''
db
database file, containing all the logic to interface with the sql database
'''

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import *
import bcrypt, jsonify
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from hashlib import sha256
# creates the database directory
Path("database") \
    .mkdir(exist_ok=True)

# "database/main.db" specifies the database file
# change it if you wish
# turn echo = True to display the sql output
engine = create_engine("sqlite:///database/main.db", echo=False)

# initializes the database
Base.metadata.create_all(engine)

# inserts a user to the database
def insert_user(username: str, password: str, public_key: str, role: str):
    with Session(engine) as session:
        user = User(username=username, password=password, public_key=public_key, role=role)
        session.add(user)
        session.commit()

# gets a user from the database
def get_user(username: str):
    with Session(engine) as session:
        return session.get(User, username)

def send_friend_request(sender_username, receiver_username):
    with Session(engine) as session:
        sender = session.get(User, sender_username)
        receiver = session.get(User, receiver_username)
        if sender and receiver:
            result = sender.send_request(receiver_username, session)
            session.commit()
            return result
        return "User not found"

def accept_friend_request(sender_username, receiver_username):
    with Session(engine) as session:
        receiver = session.get(User, receiver_username)
        if receiver:
            response = receiver.accept_request(sender_username, session)
            session.commit()
            return response
        return None

def reject_friend_request(sender_username, receiver_username):
    with Session(engine) as session:
        receiver = session.get(User, receiver_username)
        if receiver:
            response = receiver.reject_request(sender_username, session)
            session.commit()
            return response
        return None


def get_friend_requests(username: str) -> List[dict]:
    with Session(engine) as session:
        user = session.get(User, username)
        if user:
            requests = [{'username': name} for name in user.view_requests('received')]
            return requests
        return []

def get_friends_list(username: str):
    with Session(engine) as session:
        user = session.get(User, username)
        if user:
            friends_list = [{'username': friend.username, 'online_status': friend.online_status, 'role': friend.role} for friend in user.friends]
            return friends_list
        return []
    
def set_online_status(username: str, status: bool):
    with Session(engine) as session:
        user = session.query(User).filter_by(username=username).first()
        if user:
            user.online_status = status
            session.commit()

def remove_friend(username: str, friend_username: str) -> str:
    with Session(engine) as session:
        user = session.get(User, username)
        friend = session.get(User, friend_username)
        if user and friend:
            if friend in user.friends:
                user.friends.remove(friend)
                friend.friends.remove(user)
                session.commit()
                return "Friend removed successfully."
            else:
                return "User is not a friend."
        return "User not found."
    
# Insert a staff account after the database is created
def insert_staff_account():
    username = "staff_user"
    password = "staff_password"
    role = "admin"
    if get_user(username) is None:
        # Generate key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = private_key.public_key()

        # Convert keys to PEM format
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        # Store the private key in a secure manner (here we just print it)
        print(f"Private Key (store this securely): {private_key_pem}")

        # First, hash the password using SHA-256
        sha256_hashed_password = sha256(password.encode('utf-8')).hexdigest()

        # Then, hash the SHA-256 hashed password using bcrypt
        hashed_password_twice = bcrypt.hashpw(sha256_hashed_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insert user with public key
        print(f"Inserting user {username} with role {role}")
        insert_user(username, hashed_password_twice, public_key_pem, role)

        # Verify insertion by fetching the user and printing details
        user = get_user(username)
        if user:
            print(f"User '{user.username}' inserted successfully.")
            print(f"Public Key: {user.public_key}")
            print(f"Role: {user.role}")
        else:
            print("Failed to insert user.")
    else:
        print(f"User '{username}' already exists.")
        
def mute_user(username: str):
    with Session(engine) as session:
        user = session.get(User, username)
        if user:
            user.ismuted = True
            session.commit()
            return "User muted successfully."
        return "User not found."

def unmute_user(username: str):
    with Session(engine) as session:
        user = session.get(User, username)
        if user:
            user.ismuted = False
            session.commit()
            return "User unmuted successfully."
        return "User not found."


def is_user_muted(username: str) -> bool:
    with Session(engine) as session:
        user = session.get(User, username)
        if user:
            return user.ismuted
        return False

def get_all_users():
    with Session(engine) as session:
        return session.query(User).all()
    
def change_user_role(username, new_role):
    try:
        with Session(engine) as session:
            user = session.query(User).filter_by(username=username).first()
            if user:
                user.role = new_role
                session.commit()
                print(f"Changed role of {username} to {new_role}")
                return True
            else:
                return False
    except Exception as e:
        print(f"Error changing role: {e}")
        return False


# Call the function to insert the staff account
insert_staff_account()