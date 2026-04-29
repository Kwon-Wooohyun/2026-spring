from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, emit
import os, uuid, json, random, string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'band-secret-key-2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

socketio = SocketIO(app, cors_allowed_origins="*")

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory storage
teams = {}  # team_code -> team_data
users = {}  # session_id -> user_data

def generate_team_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/studio/<team_code>')
def studio(team_code):
    if team_code not in teams:
        return "팀을 찾을 수 없습니다.", 404
    return render_template('studio.html', team_code=team_code, team=teams[team_code])

@app.route('/api/create-team', methods=['POST'])
def create_team():
    data = request.json
    team_code = generate_team_code()
    while team_code in teams:
        team_code = generate_team_code()
    
    teams[team_code] = {
        'code': team_code,
        'name': data.get('team_name', '새 밴드'),
        'leader': data.get('username'),
        'members': [],
        'tracks': [],
        'created_at': str(uuid.uuid4())
    }
    return jsonify({'success': True, 'team_code': team_code})

@app.route('/api/join-team', methods=['POST'])
def join_team():
    data = request.json
    team_code = data.get('team_code', '').upper().strip()
    if team_code not in teams:
        return jsonify({'success': False, 'message': '유효하지 않은 팀 코드입니다.'})
    return jsonify({'success': True, 'team_code': team_code, 'team': teams[team_code]})

@app.route('/api/upload-track', methods=['POST'])
def upload_track():
    team_code = request.form.get('team_code')
    username = request.form.get('username')
    instrument = request.form.get('instrument')
    offset = float(request.form.get('offset', 0))

    if team_code not in teams:
        return jsonify({'success': False, 'message': '팀을 찾을 수 없습니다.'})

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '파일이 없습니다.'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '파일명이 없습니다.'})

    track_id = str(uuid.uuid4())
    filename = f"{track_id}.mp3"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    track = {
        'id': track_id,
        'username': username,
        'instrument': instrument,
        'filename': filename,
        'offset': offset,
        'volume': 1.0,
        'muted': False,
        'color': get_track_color(len(teams[team_code]['tracks']))
    }
    teams[team_code]['tracks'].append(track)

    # Notify all users in the room
    socketio.emit('track_added', {'track': track}, room=team_code)

    return jsonify({'success': True, 'track': track})

@app.route('/api/team/<team_code>')
def get_team(team_code):
    if team_code not in teams:
        return jsonify({'success': False})
    return jsonify({'success': True, 'team': teams[team_code]})

@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def get_track_color(index):
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
    return colors[index % len(colors)]

# Socket events
@socketio.on('join')
def on_join(data):
    team_code = data['team_code']
    username = data['username']
    join_room(team_code)
    
    if team_code in teams:
        if username not in teams[team_code]['members']:
            teams[team_code]['members'].append(username)
    
    emit('user_joined', {'username': username, 'members': teams[team_code]['members']}, room=team_code)

@socketio.on('leave')
def on_leave(data):
    team_code = data['team_code']
    username = data['username']
    leave_room(team_code)
    
    if team_code in teams and username in teams[team_code]['members']:
        teams[team_code]['members'].remove(username)
    
    emit('user_left', {'username': username}, room=team_code)

@socketio.on('sync_playback')
def on_sync(data):
    emit('playback_sync', data, room=data['team_code'], include_self=False)

@socketio.on('update_track')
def on_update_track(data):
    team_code = data['team_code']
    track_id = data['track_id']
    if team_code in teams:
        for t in teams[team_code]['tracks']:
            if t['id'] == track_id:
                if 'volume' in data:
                    t['volume'] = data['volume']
                if 'muted' in data:
                    t['muted'] = data['muted']
                if 'offset' in data:
                    t['offset'] = data['offset']
                break
    emit('track_updated', data, room=team_code, include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
