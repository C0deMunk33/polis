from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
import json
from werkzeug.utils import secure_filename
import os
import uuid

# Import UIInterface from ui_interface.py instead of using a duplicate version
from ui_interface import UIInterface


app = Flask(__name__)

# Update the UPLOAD_FOLDER to use absolute path
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

# Create necessary directories
for folder in [UPLOAD_FOLDER, DATA_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# File paths for persistent storage
FORUM_FILE = os.path.join(DATA_FOLDER, 'forum.json')
CHAT_FILE = os.path.join(DATA_FOLDER, 'chat.json')
AGENTS_FILE = os.path.join(DATA_FOLDER, 'agents.json')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# File operations
def load_json_file(filepath, default=[]):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                return data if data is not None else default
        else:
            # Initialize the file with default data
            save_json_file(filepath, default)
            return default
    except Exception as e:
        print(f"Error loading {filepath}: {str(e)}")
        # If there's an error, initialize with default
        save_json_file(filepath, default)
        return default

def save_json_file(filepath, data):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filepath}: {str(e)}")

# Data access functions
def get_forum_threads():
    # Initialize with empty array if file doesn't exist
    return load_json_file(FORUM_FILE, [])

def get_chat_messages():
    # Initialize with empty array if file doesn't exist
    return load_json_file(CHAT_FILE, [])

def get_agents():
    # Initialize with empty list if file doesn't exist
    all_agents = load_json_file(AGENTS_FILE, [])
    # Only return agents that haven't left
    return [agent for agent in all_agents if not agent.get('left', False)]

def get_file_size(filepath):
    try:
        return os.path.getsize(filepath)
    except:
        return 0

def get_initial_data():
    # Get list of files from uploads directory
    artifacts = []
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                artifacts.append({
                    "fileName": filename,
                    "url": f'/uploads/{filename}',
                    "size": get_file_size(filepath),
                    "uploadDate": datetime.fromtimestamp(
                        os.path.getctime(filepath)
                    ).strftime('%Y-%m-%d %H:%M:%S')
                })
    
    return {
        "artifacts": artifacts,
        "forum": get_forum_threads(),
        "chat": get_chat_messages(),
        "agents": get_agents()
    }

# Routes
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

@app.route('/api/data')
def get_data():
    return jsonify(get_initial_data())

@app.route('/api/forum/thread', methods=['POST'])
def create_thread():
    try:
        # Get the text content and author
        author = request.form.get('author', 'Anonymous')
        content = request.form.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400

        # Initialize thread data
        thread_data = {
            'threadId': str(uuid.uuid4()),
            'op': {
                'author': author,
                'content': content,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            },
            'replies': []
        }

        # Handle optional file attachment
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Add complete attachment information to the thread data
                thread_data['op']['attachment'] = {
                    'name': filename,
                    'url': f'/uploads/{filename}',
                    'type': file.content_type,
                    'size': os.path.getsize(filepath)
                }

        # Load existing threads, add new thread, and save
        forum_threads = get_forum_threads()
        forum_threads.append(thread_data)
        save_json_file(FORUM_FILE, forum_threads)

        return jsonify({
            'status': 'success',
            'threads': forum_threads
        })

    except Exception as e:
        print(f"Error creating thread: {str(e)}")
        return jsonify({'error': 'Failed to create thread'}), 500

@app.route('/api/forum/reply', methods=['POST'])
def create_reply():
    try:
        thread_id = request.args.get('thread_id')
        reply = request.json
        
        # Load existing threads
        forum_threads = get_forum_threads()
        
        # Find the thread and add the reply
        for thread in forum_threads:
            if thread['threadId'] == thread_id:
                reply['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                thread['replies'].append(reply)
                break
        
        # Save updated threads
        save_json_file(FORUM_FILE, forum_threads)
        
        return jsonify({"threads": forum_threads})
    except Exception as e:
        print(f"Error creating reply: {str(e)}")
        return jsonify({'error': 'Failed to create reply'}), 500

@app.route('/api/chat', methods=['POST'])
def send_message():
    try:
        message = request.json.get('message')
        chat_messages = get_chat_messages()
        chat_messages.append(message)
        save_json_file(CHAT_FILE, chat_messages)
        
        # Return all updated data
        return jsonify({
            "success": True,
            "chat": chat_messages,
            "forum": get_forum_threads(),  # Include forum data
            "agents": get_agents()         # Include agents data
        })
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return jsonify({'error': 'Failed to send message'}), 500

# Add this route to serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Use the absolute path when serving files
    return send_from_directory(UPLOAD_FOLDER, filename)

# Removed the duplicate UIInterface class – now using the imported UIInterface from ui_interface.py

# Create a global interface instance using the imported UIInterface
ui_interface = UIInterface()

if __name__ == '__main__':
    # Configure Flask to serve static files from the 'web' directory
    app.static_folder = '../web'
    
    # Ensure upload directory exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    # Run the server
    app.run(port=3000, debug=True) 