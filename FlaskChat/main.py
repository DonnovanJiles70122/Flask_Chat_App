import random
from flask import Flask, request, render_template, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send
from utils import generate_room_code

app = Flask(__name__)
app.config["SECRET_KEY"] = "secretKey"
socket = SocketIO(app)

# room dictionary to store information about the chat room
rooms = {}


@app.route('/', methods=["GET", "POST"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get('name')
        create = request.form.get('create', False)
        code = request.form.get('code')
        join = request.form.get('join', False)

        # if name is not input is blank send error message
        if not name:
            return render_template('home.html', error="Name is required", code=code)
        # if create button is pressed a room code will be generated
        # initialize values of new room and store values in rooms dict
        if create != False:
            room_code = generate_room_code(6, list(rooms.keys()))
            print('room_code: ' + room_code)
            new_room = {
                'members': 0,
                'messages': []
            }
            rooms[room_code] = new_room
        if join != False:
            if not code:
                return render_template('home.html', error="Please enter a room code to enter a chat room", name=name)
            if code not in rooms:
                return render_template('home.html', error="Room code invalid", name=name)
            room_code = code

        # store room_code and name in the Flask session then redirects room.html file
        session['room'] = room_code
        session['name'] = name
        return redirect(url_for('room'))
    else:
        return render_template('home.html')

# this function handles requests to the '/room' URL by checking if the user has a valid name and is
# associated with a valid chat room in the session. If these conditions are met, it retrieves the
# chat room's messages and renders an HTML template to display the chat room's contents. If any of
# the conditions are not met, the user is redirected back to the 'home' route.


@app.route('/room')
def room():
    room = session.get('room')
    name = session.get('name')
    if name is None or room is None or room not in rooms:
        return redirect(url_for('home'))
    messages = rooms[room]['messages']
    return render_template('room.html', room=room, user=name, messages=messages)

# this function is responsible for handling the WebSocket connection when a user connects to the server.
# It ensures that the user's session contains the necessary information (name and room), makes the user
# leave any previous room, joins the specified chat room, broadcasts a "user entered the chat" message,
# and updates the member count for the room.


@socket.on('connect')
def handle_connect():
    name = session.get('name')
    room = session.get('room')
    if name is None or room is None:
        return
    if room not in rooms:
        leave_room(room)
    join_room(room)
    send({
        "sender": "",
        "message": f"{name} has entered the chat"
    }, to=room)
    rooms[room]["members"] += 1

# this function handles incoming messages from clients in a WebSocket-based chat application.
# It retrieves the sender's name and the chat room they are in from the session, constructs a
# message object, sends the message to the chat room, and appends it to the chat room's message history.


@socket.on('message')
def handle_message(payload):
    room = session.get('room')
    name = session.get('name')
    if room not in rooms:
        return
    message = {
        "sender": name,
        "message": payload["message"]
    }
    send(message, to=room)
    rooms[room]["messages"].append(message)

# this function handles the disconnection of a client from the server and a chat room. It makes sure the
# user leaves the chat room, updates the member count for the room, deletes the room if it's empty, and
# sends a departure message to the chat room to inform other users that the client has left.


def handle_disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
        send({
            "message": f"{name} has left the chat",
            "sender": ""
        }, to=room)


if __name__ == "__main__":
    socket.run(app, debug=True)
