from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, 
    async_mode='eventlet',  # Plus rapide que threading
    ping_timeout=5,         # Réduit pour une détection plus rapide
    ping_interval=2,        # Réduit pour maintenir la connexion active
    cors_allowed_origins="*",
    message_queue='memory://',  # Utilise la mémoire pour une transmission plus rapide
    engineio_logger=False,      # Désactive le logging pour de meilleures performances
    logger=False
)

# Store active users
users = {}

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('chat'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    if username and username.strip():
        session['username'] = username.strip()
        return redirect(url_for('chat'))
    return redirect(url_for('index'))

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html', username=session['username'])

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        users[session['username']] = request.sid
        emit('user_list', list(users.keys()), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if 'username' in session:
        users.pop(session['username'], None)
        emit('user_list', list(users.keys()), broadcast=True)

@socketio.on('message')
def handle_message(data):
    username = session.get('username')
    if username:
        emit('message', {
            'user': username,
            'message': data['message']
        }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
