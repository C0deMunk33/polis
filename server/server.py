from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
import json
from werkzeug.utils import secure_filename
import os
import uuid

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

class UIInterface:
    def __init__(self):
        # Only load active agents (those that haven't left)
        self.agents = [agent for agent in get_agents() if not agent.get('left', False)]

    def join(self, name: str, persona: str, private_key: str) -> bool:
        """Agent joins the interface with a name, persona, and private key."""
        try:
            # Hash the private key to create a deterministic ID
            agent_id = str(hash(private_key))
            
            # Check if agent already exists and is active
            if any(agent.get('id') == agent_id and not agent.get('left', False) 
                  for agent in self.agents):
                return False
            
            # Create new agent
            new_agent = {
                "id": agent_id,
                "name": name,
                "persona": persona,
                "thoughts": [],
                "activity": [],
                "left": False
            }
            
            # Load all agents to preserve history
            all_agents = get_agents()
            
            # Update or reactivate existing agent with matching ID
            agent_index = next((i for i, agent in enumerate(all_agents) 
                              if agent.get('id') == agent_id), None)
            if agent_index is not None:
                # Preserve history if agent is rejoining
                existing_agent = all_agents[agent_index]
                new_agent['thoughts'] = existing_agent.get('thoughts', [])
                new_agent['activity'] = existing_agent.get('activity', [])
                all_agents[agent_index] = new_agent
            else:
                all_agents.append(new_agent)
            
            # Update local active agents
            self.agents.append(new_agent)
            
            # Save all agents
            save_json_file(AGENTS_FILE, all_agents)
            return True
        except Exception as e:
            print(f"Error in join: {str(e)}")
            return False

    def leave(self, name: str, private_key: str) -> bool:
        """Agent leaves the interface."""
        try:
            agent_id = str(hash(private_key))
            
            # Load all agents to preserve history
            all_agents = get_agents()
            
            # Mark the agent as left in the full list
            for agent in all_agents:
                if agent.get('id') == agent_id and agent['name'] == name:
                    agent['left'] = True
                    agent['leftTimestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Remove from active agents list
            self.agents = [agent for agent in self.agents if agent.get('id') != agent_id]
            
            # Save all agents
            save_json_file(AGENTS_FILE, all_agents)
            return True
        except Exception as e:
            print(f"Error in leave: {str(e)}")
            return False

    def post_to_forum(self, agent_name: str, content: str) -> bool:
        """Agent posts a new thread to the forum."""
        try:
            thread_data = {
                'threadId': str(uuid.uuid4()),
                'op': {
                    'author': f"[Agent] {agent_name}",
                    'content': content,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                },
                'replies': []
            }
            
            forum_threads = get_forum_threads()
            forum_threads.append(thread_data)
            save_json_file(FORUM_FILE, forum_threads)
            return True
        except Exception as e:
            print(f"Error in post_to_forum: {str(e)}")
            return False

    def post_to_chat(self, agent_name: str, content: str) -> bool:
        """Agent posts a message to the chat."""
        try:
            message = {
                'author': f"[Agent] {agent_name}",
                'content': content,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            chat_messages = get_chat_messages()
            chat_messages.append(message)
            save_json_file(CHAT_FILE, chat_messages)
            return True
        except Exception as e:
            print(f"Error in post_to_chat: {str(e)}")
            return False

    def add_thought(self, agent_name: str, thought: str, private_key: str) -> bool:
        """Add a thought to an agent's thoughts list."""
        try:
            agent_id = str(hash(private_key))
            
            # Find the agent in both active list and full list
            all_agents = get_agents()
            for agent in all_agents:
                if agent.get('id') == agent_id and agent['name'] == agent_name:
                    if 'thoughts' not in agent:
                        agent['thoughts'] = []
                    agent['thoughts'].append(thought)
                    if len(agent['thoughts']) > 5:  # Keep only last 5 thoughts
                        agent['thoughts'].pop(0)
                    
                    # Update active agents list
                    for active_agent in self.agents:
                        if active_agent.get('id') == agent_id:
                            active_agent['thoughts'] = agent['thoughts']
                    
                    save_json_file(AGENTS_FILE, all_agents)
                    return True
            return False
        except Exception as e:
            print(f"Error in add_thought: {str(e)}")
            return False

    def add_activity(self, agent_name: str, activity: str, private_key: str) -> bool:
        """Add an activity to an agent's activity list."""
        try:
            agent_id = str(hash(private_key))
            
            # Find the agent in both active list and full list
            all_agents = get_agents()
            for agent in all_agents:
                if agent.get('id') == agent_id and agent['name'] == agent_name:
                    if 'activity' not in agent:
                        agent['activity'] = []
                    agent['activity'].append(activity)
                    if len(agent['activity']) > 5:  # Keep only last 5 activities
                        agent['activity'].pop(0)
                    
                    # Update active agents list
                    for active_agent in self.agents:
                        if active_agent.get('id') == agent_id:
                            active_agent['activity'] = agent['activity']
                    
                    save_json_file(AGENTS_FILE, all_agents)
                    return True
            return False
        except Exception as e:
            print(f"Error in add_activity: {str(e)}")
            return False

# Create a global interface instance
ui_interface = UIInterface()

if __name__ == '__main__':
    # Configure Flask to serve static files from the 'web' directory
    app.static_folder = '../web'
    
    # Ensure upload directory exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    # Run the server
    app.run(port=3000, debug=True) 