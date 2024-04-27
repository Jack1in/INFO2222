'''
db
database file, containing all the logic to interface with the sql database
'''

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import *
import bcrypt 
from pathlib import Path

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
def insert_user(username: str, password: str,public_key:str):
    with Session(engine) as session:
        user = User(username=username, password=password,public_key=public_key)
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
        return None

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
            print("Formatted Friend Requests:", requests)  # Debugging line
            return requests
        return []

def get_friends_list(username: str):
    with Session(engine) as session:
        user = session.get(User, username)
        return [friend.username for friend in user.friends] if user else []