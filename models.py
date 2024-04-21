
'''
models
defines sql alchemy data models
also contains the definition for the room class used to keep track of socket.io rooms

Just a sidenote, using SQLAlchemy is a pain. If you want to go above and beyond, 
do this whole project in Node.js + Express and use Prisma instead, 
Prisma docs also looks so much better in comparison

or use SQLite, if you're not into fancy ORMs (but be mindful of Injection attacks :) )
'''
from collections import UserList
from sqlalchemy import String, Integer, ForeignKey, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from typing import Dict, List

# data models
class Base(DeclarativeBase):
    pass

# model to store user information

# model to store friend associations
friend_association = Table('friend_association', Base.metadata,
    Column('user_username', String, ForeignKey('user.username'), primary_key=True),
    Column('friend_username', String, ForeignKey('user.username'), primary_key=True)
)

# model to store friend requests
friend_request = Table('friend_request', Base.metadata,
    Column('sender_username', String, ForeignKey('user.username'), primary_key=True),
    Column('receiver_username', String, ForeignKey('user.username'), primary_key=True)
)

class User(Base):
    __tablename__ = "user"
    
    # looks complicated but basically means
    # I want a username column of type string,
    # and I want this column to be my primary key
    # then accessing john.username -> will give me some data of type string
    # in other words we've mapped the username Python object property to an SQL column of type String 
    username: Mapped[str] = mapped_column(String, primary_key=True,unique=True)
    password: Mapped[str] = mapped_column(String)
    public_key: Mapped[str] = mapped_column(String)
    friends = relationship(
        'User',
        secondary=friend_association,
        primaryjoin=(friend_association.c.user_username == username),
        secondaryjoin=(friend_association.c.friend_username == username),
        backref="added_friends"
    )

    # New relationships for friend requests
    sent_requests = relationship(
        'User',
        secondary=friend_request,
        primaryjoin=(friend_request.c.sender_username == username),
        secondaryjoin=(friend_request.c.receiver_username == username),
        backref="received_requests"
    )

    def send_request(self, friend_username: str, session: Session) -> str:
        friend = session.query(User).filter_by(username=friend_username).first()
        if not friend:
            return "Friend username does not exist."

        if friend in self.friends:
            return "Already friends."
    
        if friend in self.received_requests or friend in self.sent_requests:
            return "Friend request already sent to this user."

        self.sent_requests.append(friend)
        session.commit()
        return "Friend request sent successfully."
    
    def accept_request(self, friend_username: str, session: Session) -> str:
        friend = session.query(User).filter_by(username=friend_username).first()
        if not friend:
            return "Friend username does not exist."
        
        if friend in self.friends:
            return "Already friends."
        
        if friend not in self.received_requests:
            return "No friend request received from this user."

        self.friends.append(friend) 
        friend.friends.append(self) 
        self.received_requests.remove(friend)
        session.commit()
        return "Friend added successfully."

    def reject_request(self, friend_username: str, session: Session) -> str:
        friend = session.query(User).filter_by(username=friend_username).first()
        if not friend:
            return "Friend username does not exist."
        
        if friend not in self.received_requests:
            return "No friend request received from this user."
        self.received_requests.remove(friend)
        session.commit()
        return "Friend request rejected."

    def view_requests(self, request_type: str):
        if request_type == "sent":
            requests = [user.username for user in self.sent_requests]
        elif request_type == "received":
            requests = [user.username for user in self.received_requests]
        else:
            raise ValueError("Invalid request type. Choose 'sent' or 'received'.")

        print(f"View Requests ({request_type}):", requests)  # Debugging line
        return requests


# stateful counter used to generate the room id
class Counter():
    def __init__(self):
        self.counter = 0
    
    def get(self):
        self.counter += 1
        return self.counter

# Room class, used to keep track of which username is in which room
class Room():
    def __init__(self):
        self.counter = Counter()
        # dictionary that maps the username to the room id
        # for example self.dict["John"] -> gives you the room id of 
        # the room where John is in
        self.dict: Dict[str, int] = {}

    def create_room(self, sender: str, receiver: str) -> int:
        room_id = self.counter.get()
        self.dict[sender] = room_id
        self.dict[receiver] = room_id
        return room_id
    
    def join_room(self,  sender: str, room_id: int) -> int:
        self.dict[sender] = room_id

    def leave_room(self, user):
        if user not in self.dict.keys():
            return
        del self.dict[user]

    # gets the room id from a user
    def get_room_id(self, user: str):
        if user not in self.dict.keys():
            return None
        return self.dict[user]
    
    # get the users in a room
    def get_users(self, room_id: int):
        return [user for user, room in self.dict.items() if room == room_id]
    
