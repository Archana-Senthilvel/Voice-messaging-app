# app.py
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
from datetime import datetime
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app)

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Store active users and their rooms
users = {}
# Store conference mode status for rooms
room_conference_status = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat/<username>/<room>')
def chat(username, room):
    if room not in room_conference_status:
        room_conference_status[room] = False
    return render_template('chat.html', username=username, room=room)

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'}), 400
    
    audio_file = request.files['audio']
    username = request.form.get('username')
    room = request.form.get('room')
    
    if not audio_file:
        return jsonify({'error': 'Empty file'}), 400

    room_dir = os.path.join(UPLOAD_FOLDER, room)
    if not os.path.exists(room_dir):
        os.makedirs(room_dir)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{username}_{timestamp}.wav'
    filepath = os.path.join(room_dir, filename)
    audio_file.save(filepath)

    socketio.emit('new_message', {
        'username': username,
        'filename': filename,
        'timestamp': timestamp
    }, room=room)

    return jsonify({'success': True, 'filename': filename})

@app.route('/audio/<room>/<filename>')
def get_audio(room, filename):
    return send_file(os.path.join(UPLOAD_FOLDER, room, filename))

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    users[request.sid] = {'username': username, 'room': room}
    emit('user_joined', {'username': username}, room=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    if request.sid in users:
        del users[request.sid]
    emit('user_left', {'username': username}, room=room)

@socketio.on('conference_mode')
def handle_conference_mode(data):
    room = data['room']
    status = data['status']
    room_conference_status[room] = status
    emit('conference_mode_change', {'status': status}, room=room)

@socketio.on('audio_signal')
def handle_audio_signal(data):
    room = data['room']
    if room_conference_status.get(room, False):
        emit('audio_broadcast', data, room=room, include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True)
    