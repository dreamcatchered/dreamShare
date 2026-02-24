import os
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10 GB limit (практически без ограничений)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Хранилища
nodes = {} # node_id -> room_id
rooms = {} # room_id -> [messages]

def get_node_room(node_id):
    if node_id not in nodes:
        new_room = str(uuid.uuid4().hex[:8])
        nodes[node_id] = new_room
        rooms[new_room] = []
    return nodes[node_id]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/robots.txt')
def robots():
    return """User-agent: *
Allow: /
Sitemap: https://share.dreampartners.online/sitemap.xml
""", 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://share.dreampartners.online/</loc>
    <lastmod>2025-12-18</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
""", 200, {'Content-Type': 'application/xml'}

@app.route('/api/init/<node_id>')
def init_node(node_id):
    room_id = get_node_room(node_id)
    return jsonify({"room_id": room_id})

@app.route('/api/push', methods=['POST'])
def push():
    try:
        node_id = request.form.get('node_id')
        text = request.form.get('text')
        file = request.files.get('file')
        room_id = nodes.get(node_id)

        if not room_id: return jsonify({"error": "Node not found"}), 404

        entry = {"id": uuid.uuid4().hex[:6], "from": node_id, "type": "text"}
        if file:
            # No size limit on our side - save any file
            fname = f"{uuid.uuid4().hex[:4]}_{file.filename}"
            file.save(os.path.join(UPLOAD_FOLDER, fname))
            entry.update({"type": "file", "url": fname, "name": file.filename})
        else:
            entry.update({"content": text})

        rooms[room_id].append(entry)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "Файл слишком большой. Ограничение установлено туннелем или прокси-сервером, а не приложением."}), 413

@app.route('/api/poll/<node_id>')
def poll(node_id):
    room_id = nodes.get(node_id)
    if not room_id: return jsonify([])
    return jsonify(rooms.get(room_id, []))

@app.route('/api/participants/<node_id>')
def get_participants(node_id):
    room_id = nodes.get(node_id)
    if not room_id: return jsonify({"participants": []})
    # Get all nodes in the same room
    participants = [n_id for n_id, r_id in nodes.items() if r_id == room_id]
    return jsonify({"participants": participants})

@app.route('/api/bridge', methods=['POST'])
def bridge():
    # Связываем список всех переданных ID в одну комнату (комнату первого ID)
    target_ids = request.json.get('ids', [])
    if len(target_ids) < 2: return jsonify({"error": "Need min 2 nodes"}), 400
    
    base_room = nodes.get(target_ids[0])
    for n_id in target_ids:
        if n_id in nodes:
            old_room = nodes[n_id]
            if old_room != base_room:
                # Переносим историю (опционально)
                rooms[base_room].extend(rooms.get(old_room, []))
                nodes[n_id] = base_room
                
    return jsonify({"status": "linked", "room": base_room})

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "QS Connect",
        "short_name": "QS Connect",
        "description": "Быстрая передача файлов и сообщений между устройствами",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#F5F5F7",
        "theme_color": "#000000",
        "icons": [
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
    # Production settings
    app.run(host='0.0.0.0', port=5028, debug=False)