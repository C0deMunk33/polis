from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename

# Import UIInterface and database functions
from ui_interface import UIInterface
from database import get_forum_threads, get_chat_messages, get_agents, save_forum_thread, save_forum_reply, save_chat_message

app = Flask(__name__)

# Update the UPLOAD_FOLDER to use absolute path
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

# Create necessary directories
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            }
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

        # Save thread to database
        save_forum_thread(thread_data)

        return jsonify({
            'status': 'success',
            'threads': get_forum_threads()
        })

    except Exception as e:
        print(f"Error creating thread: {str(e)}")
        return jsonify({'error': 'Failed to create thread'}), 500

@app.route('/api/forum/reply', methods=['POST'])
def create_reply():
    try:
        thread_id = request.args.get('thread_id')
        reply = request.json
        
        # Add timestamp to reply
        reply['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save reply to database
        save_forum_reply(thread_id, reply)
        
        return jsonify({"threads": get_forum_threads()})
    except Exception as e:
        print(f"Error creating reply: {str(e)}")
        return jsonify({'error': 'Failed to create reply'}), 500

@app.route('/api/chat', methods=['POST'])
def send_message():
    try:
        message = request.json.get('message')
        
        # Add properly formatted timestamp to message
        message['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Save message to database
        save_chat_message(message)
        
        # Return all updated data
        return jsonify({
            "success": True,
            "chat": get_chat_messages(),
            "forum": get_forum_threads(),
            "agents": get_agents()
        })
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return jsonify({'error': 'Failed to send message'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# Create a global interface instance
ui_interface = UIInterface()

if __name__ == '__main__':
    # Configure Flask to serve static files from the 'web' directory
    app.static_folder = '../web'
    
    # Run the server
    app.run(port=3000, debug=True) 