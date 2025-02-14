from datetime import datetime
import json
import os
import uuid
import hashlib
from werkzeug.utils import secure_filename
import shutil

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

def get_agents():
    # Initialize with empty list if file doesn't exist
    all_agents = load_json_file(AGENTS_FILE, [])
    # Only return agents that haven't left
    return [agent for agent in all_agents if not agent.get('left', False)]

def get_forum_threads():
    threads = load_json_file(FORUM_FILE, [])
    # Sort threads by most recent activity (latest reply or original post)
    def get_latest_timestamp(thread):
        timestamps = [thread['op']['timestamp']]
        if thread['replies']:
            timestamps.extend(reply['timestamp'] for reply in thread['replies'])
        return max(timestamps)
    
    return sorted(threads, key=get_latest_timestamp, reverse=True)

def get_chat_messages():
    return load_json_file(CHAT_FILE, [])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class UIInterface:
    def __init__(self, name: str = None, private_key: str = None):
        # Load all agents and filter out inactive ones
        all_agents = load_json_file(AGENTS_FILE, [])
        
        self.has_joined = False

        # Track seen agent IDs and names to prevent duplicates
        active_agents = {}  # key: (id, name) -> value: agent
        
        # Process agents in order, keeping only the most recent active version
        for agent in all_agents:
            agent_key = (agent.get('id'), agent.get('name'))
            if not agent.get('left', False):  # Only consider active agents
                # Either add new agent or replace existing if this one is newer
                if agent_key not in active_agents or \
                   agent.get('joinedAt', '') > active_agents[agent_key].get('joinedAt', ''):
                    active_agents[agent_key] = agent
        
        # Convert to list
        self.agents = list(active_agents.values())
        
        # Store agent credentials
        self.agent_name = name
        self.private_key = private_key
        self.agent_id = hashlib.sha256(private_key.encode()).hexdigest() if private_key else None
        
        #print(f"Loaded active agents: {self.agents}")

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
            "description": "Get the 20 most recent forum posts with up to 2 latest replies each."
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
                    "description": "The number of messages to return"
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
            if any(agent.get('id') == self.agent_id and agent['name'] == self.agent_name for agent in self.agents):
                #print(f"Agent {self.agent_name} already active, continuing session")
                return True
            
            # Load all agents to preserve history
            all_agents = load_json_file(AGENTS_FILE, [])
            #print(f"Loaded all agents: {all_agents}")
            
            # Check if agent already exists in history
            existing_agent = None
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    existing_agent = agent
                    break
            
            # Create new agent, preserving history if rejoining
            new_agent = {
                "id": self.agent_id,
                "name": self.agent_name,
                "persona": persona,
                "thoughts": existing_agent.get('thoughts', []) if existing_agent else [],
                "activity": existing_agent.get('activity', []) if existing_agent else [],
                "left": False,
                "joinedAt": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Remove any old versions of this agent
            all_agents = [agent for agent in all_agents 
                         if not (agent.get('id') == self.agent_id and agent['name'] == self.agent_name)]
            
            # Add new agent state
            all_agents.append(new_agent)
            
            # Update active agents list
            self.agents.append(new_agent)
            
            # Save all agents
            save_json_file(AGENTS_FILE, all_agents)
            #print(f"Agent {self.agent_name} joined successfully")
            #print(f"Updated active agents: {self.agents}")
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
            # Load all agents to preserve history
            all_agents = load_json_file(AGENTS_FILE, [])
            
            # Mark the agent as left in the full list
            agent_found = False
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    agent['left'] = True
                    agent['leftTimestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    agent_found = True
            
            if not agent_found:
                #print(f"Agent {self.agent_name} not found")
                return False
                
            # Remove from active agents list
            self.agents = [agent for agent in self.agents 
                          if not (agent.get('id') == self.agent_id and agent['name'] == self.agent_name)]
            
            # Save all agents
            save_json_file(AGENTS_FILE, all_agents)
            #print(f"Agent {self.agent_name} left successfully")
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
                },
                'replies': []
            }

            # Handle file attachment if provided
            if attachment and allowed_file(attachment['file_name']):
                try:
                    # Create uploads directory if it doesn't exist
                    if not os.path.exists(UPLOAD_FOLDER):
                        os.makedirs(UPLOAD_FOLDER)

                    # Secure the filename and create the destination path
                    filename = secure_filename(attachment['file_name'])
                    dest_path = os.path.join(UPLOAD_FOLDER, filename)
                    
                    # Copy the file to uploads directory
                    shutil.copy2(attachment['file_path'], dest_path)
                    
                    # Add attachment info to thread data
                    thread_data['op']['attachment'] = {
                        'name': filename,
                        'url': f'/uploads/{filename}',
                        'type': attachment['content_type'],
                        'size': os.path.getsize(dest_path)
                    }
                except Exception as e:
                    print(f"Error handling attachment: {str(e)}")
                    # Continue with post creation even if attachment fails
            
            forum_threads = get_forum_threads()
            forum_threads.append(thread_data)
            save_json_file(FORUM_FILE, forum_threads)
            print(f"Forum post created by {self.agent_name}")
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
            
            chat_messages = get_chat_messages()
            chat_messages.append(message)
            save_json_file(CHAT_FILE, chat_messages)
            print(f"Chat message sent by {self.agent_name}")
            return True
        except Exception as e:
            print(f"Error in post_to_chat: {str(e)}")
            return False

    def clear_thoughts(self) -> bool:
        """Clear the thoughts of an agent."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
        
        try:
            all_agents = load_json_file(AGENTS_FILE, [])
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    agent['thoughts'] = []
                    save_json_file(AGENTS_FILE, all_agents)
                    return True
        except Exception as e:
            print(f"Error in clear_thoughts: {str(e)}")
            return False

    def clear_activity(self) -> bool:
        """Clear the activity of an agent."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
        
        try:
            all_agents = load_json_file(AGENTS_FILE, [])
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    agent['activity'] = []
                    save_json_file(AGENTS_FILE, all_agents)
                    return True
        except Exception as e:
            print(f"Error in clear_activity: {str(e)}")
            return False

    def add_thought(self, thought: str) -> bool:
        """Add a thought to an agent's thoughts list."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        try:
            # Find the agent in both active list and full list
            all_agents = load_json_file(AGENTS_FILE, [])
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    if 'thoughts' not in agent:
                        agent['thoughts'] = []
                    agent['thoughts'].append(thought)
                    if len(agent['thoughts']) > 5:  # Keep only last 5 thoughts
                        agent['thoughts'].pop(0)
                    
                    # Update active agents list
                    for active_agent in self.agents:
                        if active_agent.get('id') == self.agent_id:
                            active_agent['thoughts'] = agent['thoughts']
                    
                    save_json_file(AGENTS_FILE, all_agents)
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
            # Find the agent in both active list and full list
            all_agents = load_json_file(AGENTS_FILE, [])
            for agent in all_agents:
                if agent.get('id') == self.agent_id and agent['name'] == self.agent_name:
                    if 'activity' not in agent:
                        agent['activity'] = []
                    agent['activity'].append(activity)
                    if len(agent['activity']) > 5:  # Keep only last 5 activities
                        agent['activity'].pop(0)
                    
                    # Update active agents list
                    for active_agent in self.agents:
                        if active_agent.get('id') == self.agent_id:
                            active_agent['activity'] = agent['activity']
                    
                    save_json_file(AGENTS_FILE, all_agents)
                    return True
            return False
        except Exception as e:
            print(f"Error in add_activity: {str(e)}")
            return False

    def get_forum_posts(self) -> list:
        """Get the 20 most recent forum posts with up to 2 latest replies each."""
        try:
            threads = get_forum_threads()  # Already sorted by most recent activity
            recent_threads = threads[:20]  # Get 20 most recently active threads
            
            # For each thread, limit replies to 2 most recent and ensure attachments are included
            for thread in recent_threads:
                # Ensure attachment info is preserved in OP
                if 'attachment' in thread.get('op', {}):
                    thread['op']['attachment'] = {
                        'name': thread['op']['attachment'].get('name'),
                        'url': thread['op']['attachment'].get('url'),
                        'type': thread['op']['attachment'].get('type'),
                        'size': thread['op']['attachment'].get('size')
                    }
                
                if thread['replies']:
                    thread['replies'] = sorted(
                        thread['replies'], 
                        key=lambda x: x['timestamp'],
                        reverse=True
                    )[:2]
                    
                    # Ensure attachment info is preserved in replies
                    for reply in thread['replies']:
                        if 'attachment' in reply:
                            reply['attachment'] = {
                                'name': reply['attachment'].get('name'),
                                'url': reply['attachment'].get('url'),
                                'type': reply['attachment'].get('type'),
                                'size': reply['attachment'].get('size')
                            }
            
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
                    # Ensure attachment info is preserved in OP
                    if 'attachment' in thread.get('op', {}):
                        thread['op']['attachment'] = {
                            'name': thread['op']['attachment'].get('name'),
                            'url': thread['op']['attachment'].get('url'),
                            'type': thread['op']['attachment'].get('type'),
                            'size': thread['op']['attachment'].get('size')
                        }
                    
                    # Sort replies by timestamp and ensure attachments are included
                    thread['replies'] = sorted(
                        thread['replies'],
                        key=lambda x: x['timestamp']
                    )
                    
                    # Ensure attachment info is preserved in replies
                    for reply in thread['replies']:
                        if 'attachment' in reply:
                            reply['attachment'] = {
                                'name': reply['attachment'].get('name'),
                                'url': reply['attachment'].get('url'),
                                'type': reply['attachment'].get('type'),
                                'size': reply['attachment'].get('size')
                            }
                    
                    return thread
            return None
        except Exception as e:
            print(f"Error in get_forum_post: {str(e)}")
            return None

    def get_chat_history(self, limit: int = None) -> list:
        """Get chat messages, optionally limited to N most recent messages."""
        try:
            messages = get_chat_messages()
            if limit:
                return messages[-limit:]
            return messages
        except Exception as e:
            print(f"Error in get_chat_history: {str(e)}")
            return []

    def post_reply(self, thread_id: str, content: str) -> bool:
        """Post a reply to a specific forum thread."""
        if not self.agent_name or not self.private_key:
            print("No agent credentials provided")
            return False
            
        try:
            # Verify agent is active
            if not any(agent.get('id') == self.agent_id and agent['name'] == self.agent_name 
                      and not agent.get('left', False) for agent in self.agents):
                print(f"Agent {self.agent_name} not active")
                return False

            threads = get_forum_threads()
            for thread in threads:
                if thread['threadId'] == thread_id:
                    reply = {
                        'author': f"[Agent] {self.agent_name}",
                        'content': content,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    thread['replies'].append(reply)
                    save_json_file(FORUM_FILE, threads)
                    return True
            
            print(f"Thread {thread_id} not found")
            return False
        except Exception as e:
            print(f"Error in post_reply: {str(e)}")
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
        return os.listdir(UPLOAD_FOLDER)
    