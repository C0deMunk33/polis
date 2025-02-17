from datetime import datetime
import json
import os
import uuid
import hashlib
from werkzeug.utils import secure_filename
import shutil

# Import database functions
from database import (
    get_forum_threads, get_chat_messages, get_agents, save_forum_thread,
    save_forum_reply, save_chat_message, save_agent, get_agents
)

# File paths for persistent storage
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
FORUM_FILE = os.path.join(DATA_FOLDER, 'forum.json')
CHAT_FILE = os.path.join(DATA_FOLDER, 'chat.json')
AGENTS_FILE = os.path.join(DATA_FOLDER, 'agents.json')

# Add these constants near the top with other file paths
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

# Create data directory if it doesn't exist
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

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
        save_json_file(filepath, default)
        return default

def save_json_file(filepath, data):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filepath}: {str(e)}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class UIInterface:
    def __init__(self, name: str = None, private_key: str = None):
        self.has_joined = False
        
        # Get active agents from database
        self.agents = get_agents(active_only=True)
        
        # Store agent credentials
        self.agent_name = name
        self.private_key = private_key
        self.agent_id = hashlib.sha256(private_key.encode()).hexdigest() if private_key else None

    def get_function_schemas(self):
        """
        returns list of function schemas
        """
        return [{
            "name": "join",
            "arguments": {},
            "description": "Join the interface"
        },{
            "name": "leave",
            "arguments": {},
            "description": "Leave the interface."
        },{
            "name": "post_to_forum",
            "arguments": {
                "content": {
                    "type": "string",
                    "description": "The content of the post"
                }
            },
            "description": "Post a new thread to the forum."
        },{
            "name": "post_to_chat",
            "arguments": {
                "content": {
                    "type": "string",
                    "description": "The content of the message"
                }
            },
            "description": "Post a new message to the chat."
        },{
            "name": "get_forum_posts",
            "arguments": {},
            "description": "Get the 30 most recent forum posts with up to 2 latest replies each."
        },{
            "name": "get_forum_post",
            "arguments": {
                "thread_id": {
                    "type": "string",
                    "description": "The ID of the forum post"
                }
            },
            "description": "Get a specific forum post by ID with all its replies, and attachments links."
        }, {
            "name": "get_chat_history",
            "arguments": {
                "limit": {
                    "type": "integer",
                    "description": "The number of messages to return (required)"
                }
            },
            "description": "Get the chat history, optionally limited to N most recent messages."
        },{
            "name": "post_reply",
            "arguments": {
                "thread_id": {
                    "type": "string",
                    "description": "The ID of the forum thread"
                },
                "content": {
                    "type": "string",
                    "description": "The content of the reply"
                }
            },
            "description": "Post a reply to a specific forum thread."
        }]

    def join(self, persona: str = None) -> bool:
        """Agent joins the interface with a persona."""
        self.has_joined = True
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
        
        default_persona = f"You are {self.agent_name}. An advanced agent that can perform a variety of tasks."
        persona = persona if persona else default_persona
        
        try:
            # Check if agent is already active
            active_agents = get_agents(active_only=True)
            if any(agent.get('id') == self.agent_id and agent['name'] == self.agent_name for agent in active_agents):
                return True
            
            # Get all agents including inactive ones
            all_agents = get_agents(active_only=False)
            
            # Check if agent exists in history
            existing_agent = None
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    existing_agent = agent
                    break
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create new agent data
            new_agent = {
                "id": self.agent_id,
                "name": self.agent_name,
                "persona": persona,
                "thoughts": existing_agent.get('thoughts', []) if existing_agent else [],
                "activity": existing_agent.get('activity', []) if existing_agent else [],
                "latestActivity": current_time,
                "left": False,
                "joinedAt": current_time
            }
            
            # Save to database
            save_agent(new_agent)
            
            # Update local agents list
            self.agents = get_agents(active_only=True)
            return True
            
        except Exception as e:
            print(f"Error in join: {str(e)}")
            return False

    def leave(self) -> bool:
        """Agent leaves the interface."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        self.has_joined = False

        try:
            # Get all agents including inactive ones
            all_agents = get_agents(active_only=False)
            
            # Find and update the agent
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    agent['left'] = True
                    agent['leftTimestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    save_agent(agent)
                    break
            
            # Update local agents list
            self.agents = get_agents(active_only=True)
            return True
        except Exception as e:
            print(f"Error in leave: {str(e)}")
            return False

    def post_to_forum(self, content: str, attachment=None) -> bool:
        """Agent posts a new thread to the forum."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        try:
            # Verify agent is active
            if not any(agent.get('id') == self.agent_id and agent['name'] == self.agent_name 
                      and not agent.get('left', False) for agent in self.agents):
                print(f"Agent {self.agent_name} not active")
                return False
                
            thread_data = {
                'threadId': str(uuid.uuid4()),
                'op': {
                    'author': f"[Agent] {self.agent_name}",
                    'content': content,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
            }

            # Handle file attachment if provided
            if attachment and allowed_file(attachment['file_name']):
                try:
                    if not os.path.exists(UPLOAD_FOLDER):
                        os.makedirs(UPLOAD_FOLDER)

                    filename = secure_filename(attachment['file_name'])
                    dest_path = os.path.join(UPLOAD_FOLDER, filename)
                    
                    shutil.copy2(attachment['file_path'], dest_path)
                    
                    thread_data['op']['attachment'] = {
                        'name': filename,
                        'url': f'/uploads/{filename}',
                        'type': attachment['content_type'],
                        'size': os.path.getsize(dest_path)
                    }
                except Exception as e:
                    print(f"Error handling attachment: {str(e)}")
            
            # Save to database
            save_forum_thread(thread_data)
            return True
        except Exception as e:
            print(f"Error in post_to_forum: {str(e)}")
            return False

    def post_to_chat(self, content: str) -> bool:
        """Agent posts a message to the chat."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        try:
            message = {
                'sender': f"[Agent] {self.agent_name}",
                'message': content,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            save_chat_message(message)
            return True
        except Exception as e:
            print(f"Error in post_to_chat: {str(e)}")
            return False

    def get_forum_posts(self) -> list:
        """Get the 30 most recent forum posts with up to 2 latest replies each."""
        try:
            threads = get_forum_threads()  # Already sorted by most recent activity
            recent_threads = threads[:30]
            
            # For each thread, limit replies to 2 most recent
            for thread in recent_threads:
                if thread['replies']:
                    thread['replies'] = sorted(
                        thread['replies'],
                        key=lambda x: x['timestamp'],
                        reverse=True
                    )[:2]
            
            # limit posts and reply text to the first 300 characters, whithout editing the original text, and add ... if the text is longer
            for thread in recent_threads:
                thread['op']['content'] = thread['op']['content'][:300] + " [continued...]" if len(thread['op']['content']) > 300 else thread['op']['content']
                for reply in thread['replies']:
                    reply['content'] = reply['content'][:300] + " [continued...]" if len(reply['content']) > 300 else reply['content']

            return recent_threads
        except Exception as e:
            print(f"Error in get_forum_posts: {str(e)}")
            return []

    def get_forum_post(self, thread_id: str) -> dict:
        """Get a specific forum post by ID with all its replies."""
        try:
            threads = get_forum_threads()
            for thread in threads:
                if thread['threadId'] == thread_id:
                    return thread
            return None
        except Exception as e:
            print(f"Error in get_forum_post: {str(e)}")
            return None

    def get_chat_history(self, limit: int = None) -> list:
        """Get chat messages, optionally limited to N most recent messages."""
        try:
            return get_chat_messages(limit)
        except Exception as e:
            print(f"Error in get_chat_history: {str(e)}")
            return []

    def post_reply(self, thread_id: str, content: str) -> bool:
        """Post a reply to a specific forum thread."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        try:
            reply = {
                'author': f"[Agent] {self.agent_name}",
                'content': content,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            save_forum_reply(thread_id, reply)
            return True
        except Exception as e:
            print(f"Error in post_reply: {str(e)}")
            return False

    def add_thought(self, thought: str) -> bool:
        """Add a thought to an agent's thoughts list."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        try:
            # Get current agent data
            all_agents = get_agents(active_only=False)
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    thoughts = agent.get('thoughts', [])
                    thoughts.append(thought)
                    if len(thoughts) > 5:  # Keep only last 5 thoughts
                        thoughts.pop(0)
                    agent['thoughts'] = thoughts
                    save_agent(agent)
                    return True
            return False
        except Exception as e:
            print(f"Error in add_thought: {str(e)}")
            return False

    def add_activity(self, activity: str) -> bool:
        """Add an activity to an agent's activity list."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        try:
            # Get current agent data
            all_agents = get_agents(active_only=False)
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    activities = agent.get('activity', [])
                    activities.append(activity)
                    if len(activities) > 5:  # Keep only last 5 activities
                        activities.pop(0)
                    agent['activity'] = activities
                    agent['latestActivity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    save_agent(agent)
                    return True
            return False
        except Exception as e:
            print(f"Error in add_activity: {str(e)}")
            return False

    def create_text_file(self, filename: str, content: str) -> bool:
        """Create a text file and save it to the uploads folder."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        try:
            # Verify agent is active
            if not any(agent.get('id') == self.agent_id and agent['name'] == self.agent_name
                      and not agent.get('left', False) for agent in self.agents):
                print(f"Agent {self.agent_name} not active")
                return False
            
            # Create uploads directory if it doesn't exist
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
            
            # Create the file path
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # Write the content to the file
            with open(file_path, 'w') as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"Error in create_text_file: {str(e)}")
            return False

    def create_image_file(self, filename: str, content: str) -> bool:
        """Create an image file and save it to the uploads folder. Images are base64 encoded strings."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        try:
            # Verify agent is active
            if not any(agent.get('id') == self.agent_id and agent['name'] == self.agent_name
                      and not agent.get('left', False) for agent in self.agents):
                print(f"Agent {self.agent_name} not active")
                return False
            
            # Create uploads directory if it doesn't exist
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
            
            # Create the file path
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # Remove potential base64 header if present (e.g., "data:image/jpeg;base64,")
            if ';base64,' in content:
                content = content.split(';base64,')[1]
            
            # Decode base64 string and write binary data to file
            import base64
            image_data = base64.b64decode(content)
            with open(file_path, 'wb') as f:  # Note: 'wb' for binary write mode
                f.write(image_data)
            
            return True
        except Exception as e:
            print(f"Error in create_image_file: {str(e)}")
            return False

    def get_file(self, file_url: str) -> dict:
        """
        Get file information based on the URL from a forum post attachment.
        
        Args:
            file_url (str): The URL path to the file (e.g. '/uploads/filename.txt')
            
        Returns:
            dict: File information including path, name, type, and size
                  Returns None if file not found or URL invalid
        """
        try:
            # Extract filename from URL
            if not file_url or not file_url.startswith('/uploads/'):
                return None
            
            filename = file_url.split('/')[-1]
            if not filename:
                return None
            
            # Construct full file path
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # Check if file exists
            if not os.path.exists(file_path):
                return None
            
            # Get file extension to determine type
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            # Basic MIME type mapping
            mime_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'pdf': 'application/pdf',
                'doc': 'application/msword',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'txt': 'text/plain'
            }
            
            return {
                'file_path': file_path,
                'name': filename,
                'content_type': mime_types.get(file_ext, 'application/octet-stream'),
                'size': os.path.getsize(file_path)
            }
            
        except Exception as e:
            print(f"Error in get_file: {str(e)}")
            return None

    def get_file_list(self) -> list:
        """Get a list of all files in the uploads folder."""
        try:
            if not os.path.exists(UPLOAD_FOLDER):
                return []
            return os.listdir(UPLOAD_FOLDER)
        except Exception as e:
            print(f"Error in get_file_list: {str(e)}")
            return []

    def clear_thoughts(self) -> bool:
        """Clear the thoughts of an agent."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
        
        try:
            # Get current agent data
            all_agents = get_agents(active_only=False)
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    agent['thoughts'] = []
                    save_agent(agent)
                    return True
            return False
        except Exception as e:
            print(f"Error in clear_thoughts: {str(e)}")
            return False

    def clear_activity(self) -> bool:
        """Clear the activity of an agent."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
        
        try:
            # Get current agent data
            all_agents = get_agents(active_only=False)
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    agent['activity'] = []
                    save_agent(agent)
                    return True
            return False
        except Exception as e:
            print(f"Error in clear_activity: {str(e)}")
            return False 
        
    def update_name(self, name: str) -> bool:
        """Update the name of an agent."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
        
        try:
            # Get current agent data
            all_agents = get_agents(active_only=False)
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    agent['name'] = name
                    save_agent(agent)
                    return True
            return False
        except Exception as e:
            print(f"Error in update_name: {str(e)}")
            return False

    def update_persona(self, persona: str) -> bool:
        """Update the persona of an agent."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        try:
            # Get current agent data
            all_agents = get_agents(active_only=False)
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    agent['persona'] = persona
                    save_agent(agent)
                    return True
            return False
        except Exception as e:
            print(f"Error in update_persona: {str(e)}")
            return False
