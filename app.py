import os
import uuid
import time
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    print("WARNING: apscheduler not installed. Install with: pip install apscheduler")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # Лимит 10 GB

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Storage
nodes = {}  # node_id -> room_id
rooms = {}  # room_id -> {'messages':[], 'last_activity': timestamp}
FILES_INFO = {}  # filename -> {'path': str, 'uploaded_at': timestamp, 'size': int}

# File to persist state across reboots
STATE_FILE = 'share_state.json'
STATE_CLEANUP_INTERVAL_HOURS = 24  # Запуск очистки каждые 24 часа
FILE_MAX_AGE_HOURS = 24  # Удалять всё старше 24 часов

def load_state():
    """Загрузка состояния из файла"""
    global nodes, rooms, FILES_INFO
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                nodes = state.get('nodes', {})
                rooms = state.get('rooms', {})
                FILES_INFO = state.get('files_info', {})
                print(f"Loaded state: {len(nodes)} nodes, {len(rooms)} rooms, {len(FILES_INFO)} files")
    except Exception as e:
        print(f"Error loading state: {e}")

def save_state():
    """Сохранение состояния в файл"""
    try:
        state = {
            'nodes': nodes,
            'rooms': rooms,
            'files_info': FILES_INFO,
            'saved_at': datetime.utcnow().isoformat()
        }
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving state: {e}")

def cleanup_old_files():
    """Надежное удаление старых файлов, сообщений и пустых комнат"""
    print(f"[{datetime.utcnow()}] Running cleanup...")
    current_time = time.time()
    deleted_files = 0
    deleted_bytes = 0
    
    # 1. Очистка старых сообщений во всех комнатах (включая файлы)
    for room_id, room_data in list(rooms.items()):
        if isinstance(room_data, dict):
            messages = room_data.get('messages',[])
            valid_messages =[]
            for msg in messages:
                age_hours = (current_time - msg.get('timestamp', current_time)) / 3600
                if age_hours > FILE_MAX_AGE_HOURS:
                    # Сообщение устарело - если это файл, удаляем его
                    if msg.get('type') == 'file':
                        filename = msg.get('url')
                        if filename in FILES_INFO:
                            file_path = FILES_INFO[filename].get('path')
                            try:
                                if file_path and os.path.exists(file_path):
                                    deleted_bytes += os.path.getsize(file_path)
                                    os.remove(file_path)
                                    deleted_files += 1
                            except Exception as e:
                                print(f"Error deleting file {filename}: {e}")
                            FILES_INFO.pop(filename, None)
                else:
                    valid_messages.append(msg)
            rooms[room_id]['messages'] = valid_messages

    # 2. Очистка FILES_INFO от забытых записей
    for filename, info in list(FILES_INFO.items()):
        age_hours = (current_time - info.get('uploaded_at', 0)) / 3600
        if age_hours > FILE_MAX_AGE_HOURS:
            file_path = info.get('path', os.path.join(UPLOAD_FOLDER, filename))
            try:
                if os.path.exists(file_path):
                    deleted_bytes += os.path.getsize(file_path)
                    os.remove(file_path)
                    deleted_files += 1
            except Exception as e:
                print(f"Error deleting info file {filename}: {e}")
            FILES_INFO.pop(filename, None)

    # 3. Полная очистка папки uploads от физических файлов-сирот
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if filename not in FILES_INFO and os.path.isfile(file_path):
                try:
                    file_mtime = os.path.getmtime(file_path)
                    age_hours = (current_time - file_mtime) / 3600
                    if age_hours > FILE_MAX_AGE_HOURS:
                        deleted_bytes += os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_files += 1
                except Exception as e:
                    print(f"Error deleting orphaned file {filename}: {e}")
    except Exception as e:
        print(f"Error listing uploads folder: {e}")

    # 4. Удаление неактивных комнат
    rooms_to_delete =[]
    for room_id, room_data in list(rooms.items()):
        if isinstance(room_data, dict):
            last_activity = room_data.get('last_activity', 0)
        else:
            last_activity = 0
            
        age_hours = (current_time - last_activity) / 3600
        
        if age_hours > FILE_MAX_AGE_HOURS:
            nodes_using_room =[n for n, r in nodes.items() if r == room_id]
            if not nodes_using_room:
                rooms_to_delete.append(room_id)
                
    for room_id in rooms_to_delete:
        del rooms[room_id]
        print(f"Deleted inactive room: {room_id}")

    # 5. Удаление узлов с несуществующими комнатами
    nodes_to_delete =[node_id for node_id, room_id in nodes.items() if room_id not in rooms]
    for node_id in nodes_to_delete:
        del nodes[node_id]

    save_state()
    print(f"[{datetime.utcnow()}] Cleanup complete: deleted {deleted_files} files ({deleted_bytes / 1024 / 1024:.2f} MB)")
    return deleted_files, deleted_bytes

def get_node_room(node_id):
    if node_id not in nodes:
        new_room = str(uuid.uuid4().hex[:8])
        nodes[node_id] = new_room
        rooms[new_room] = {
            'messages':[],
            'last_activity': time.time()
        }
    return nodes[node_id]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/robots.txt')
def robots():
    return "User-agent: *\nAllow: /\nSitemap: https://share.dreampartners.online/sitemap.xml\n", 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n  <url>\n    <loc>https://share.dreampartners.online/</loc>\n    <lastmod>2025-12-18</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n</urlset>\n", 200, {'Content-Type': 'application/xml'}

@app.route('/api/init/<node_id>')
def init_node(node_id):
    room_id = get_node_room(node_id)
    return jsonify({"room_id": room_id})

@app.route('/api/push', methods=['POST'])
def push():
    try:
        node_id = request.form.get('node_id')
        text = request.form.get('text')
        is_code = request.form.get('is_code') == 'true'
        file = request.files.get('file')
        room_id = nodes.get(node_id)
        
        if not room_id:
            return jsonify({"error": "Node not found"}), 404
        
        entry = {"id": uuid.uuid4().hex[:8], "from": node_id, "type": "text", "timestamp": time.time()}
        
        if file:
            fname = f"{uuid.uuid4().hex[:4]}_{file.filename}"
            file_path = os.path.join(UPLOAD_FOLDER, fname)
            try:
                file.save(file_path)
            except PermissionError:
                return jsonify({"error": "Permission denied: cannot write to uploads folder. Check folder permissions."}), 500
            
            FILES_INFO[fname] = {
                'path': file_path,
                'uploaded_at': time.time(),
                'size': os.path.getsize(file_path)
            }
            
            entry.update({"type": "file", "url": fname, "name": file.filename})
        else:
            entry.update({"content": text, "is_code": is_code})
        
        if room_id not in rooms:
            rooms[room_id] = {'messages':[], 'last_activity': time.time()}
            
        rooms[room_id]['messages'].append(entry)
        rooms[room_id]['last_activity'] = time.time()
        
        save_state()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete', methods=['POST'])
def delete_message():
    """Моментальное удаление сообщения и прикрепленного файла для всех"""
    try:
        data = request.json
        node_id = data.get('node_id')
        msg_id = data.get('msg_id')
        
        room_id = nodes.get(node_id)
        if not room_id or room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        messages = rooms[room_id].get('messages',[])
        msg_to_delete = None
        
        for msg in messages:
            if msg.get('id') == msg_id:
                msg_to_delete = msg
                break
                
        if not msg_to_delete:
            return jsonify({"error": "Message not found"}), 404
            
        # Если это файл, немедленно удаляем его с жесткого диска
        if msg_to_delete.get('type') == 'file':
            filename = msg_to_delete.get('url')
            # Удаляем из FILES_INFO и с диска
            if filename in FILES_INFO:
                file_path = FILES_INFO[filename].get('path', os.path.join(UPLOAD_FOLDER, filename))
                if os.path.exists(file_path):
                    os.remove(file_path)
                del FILES_INFO[filename]
            else:
                # На всякий случай проверяем прямо в папке
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        # Удаляем из истории комнаты
        messages.remove(msg_to_delete)
        save_state()
        
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large. Check proxy/upload limits."}), 413

@app.route('/api/poll/<node_id>')
def poll(node_id):
    room_id = nodes.get(node_id)
    if not room_id:
        return jsonify([])
    room_data = rooms.get(room_id, {})
    if isinstance(room_data, dict):
        messages = room_data.get('messages',[])
    else:
        messages = room_data if isinstance(room_data, list) else[]
    return jsonify(messages)

@app.route('/api/participants/<node_id>')
def get_participants(node_id):
    room_id = nodes.get(node_id)
    if not room_id:
        return jsonify({"participants": []})
    participants =[n_id for n_id, r_id in nodes.items() if r_id == room_id]
    return jsonify({"participants": participants})

@app.route('/api/bridge', methods=['POST'])
def bridge():
    target_ids = request.json.get('ids',[])
    if len(target_ids) < 2:
        return jsonify({"error": "Need min 2 nodes"}), 400
    
    base_room = nodes.get(target_ids[0])
    if not base_room:
        return jsonify({"error": "Base node not found"}), 404
    
    for n_id in target_ids:
        if n_id in nodes:
            old_room = nodes[n_id]
            if old_room != base_room:
                if old_room in rooms and base_room in rooms:
                    if isinstance(rooms[base_room], dict):
                        if isinstance(rooms[old_room], dict):
                            rooms[base_room]['messages'].extend(rooms[old_room].get('messages', []))
                        else:
                            rooms[base_room]['messages'].extend(rooms[old_room] if isinstance(rooms[old_room], list) else [])
                    elif isinstance(rooms[base_room], list):
                        if isinstance(rooms[old_room], dict):
                            rooms[base_room].extend(rooms[old_room].get('messages',[]))
                        else:
                            rooms[base_room].extend(rooms[old_room] if isinstance(rooms[old_room], list) else [])
                    rooms[base_room]['last_activity'] = time.time()
                nodes[n_id] = base_room
                
    return jsonify({"status": "linked", "room": base_room})

@app.route('/api/cleanup', methods=['POST'])
def manual_cleanup():
    deleted_files, deleted_bytes = cleanup_old_files()
    return jsonify({
        "status": "ok",
        "deleted_files": deleted_files,
        "deleted_bytes": deleted_bytes
    })

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "QS Connect",
        "short_name": "QS Connect",
        "description": "Fast file and message transfer between devices",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#F5F5F7",
        "theme_color": "#000000",
        "icons":[
            {
                "src": "https://api.dreampartners.online/icons/share/android-chrome-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "https://api.dreampartners.online/icons/share/android-chrome-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

if __name__ == '__main__':
    load_state()
    cleanup_old_files()
    
    if APSCHEDULER_AVAILABLE:
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            func=cleanup_old_files,
            trigger=IntervalTrigger(hours=STATE_CLEANUP_INTERVAL_HOURS),
            id='cleanup_job',
            name='Clean up old files and rooms',
            replace_existing=True
        )
        scheduler.start()
        print(f"Scheduler started: cleanup every {STATE_CLEANUP_INTERVAL_HOURS} hours")
    
    print(f"Files older than {FILE_MAX_AGE_HOURS} hours will be deleted automatically.")
    app.run(host='0.0.0.0', port=5028, debug=False)