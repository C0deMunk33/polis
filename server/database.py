import sqlite3
from datetime import datetime
import json
import os

# Get the absolute path for the database file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'ui.db')

# Ensure the data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS forum_threads (
            thread_id TEXT PRIMARY KEY,
            op_author TEXT,
            op_content TEXT,
            op_timestamp TEXT,
            op_attachment TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS forum_replies (
            reply_id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT,
            author TEXT,
            content TEXT,
            timestamp TEXT,
            attachment TEXT,
            FOREIGN KEY (thread_id) REFERENCES forum_threads(thread_id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT,
            name TEXT,
            persona TEXT,
            thoughts TEXT,
            activity TEXT,
            left BOOLEAN DEFAULT FALSE,
            joined_at TEXT,
            left_timestamp TEXT,
            PRIMARY KEY (agent_id, name)
        )
    ''')
    
    conn.commit()
    conn.close()

def dict_factory(cursor, row):
    """Convert database rows to dictionaries"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db():
    """Get database connection with row factory set"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn

def save_forum_thread(thread_data):
    """Save a forum thread to the database"""
    conn = get_db()
    c = conn.cursor()
    
    # Save thread
    c.execute('''
        INSERT INTO forum_threads (thread_id, op_author, op_content, op_timestamp, op_attachment)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        thread_data['threadId'],
        thread_data['op']['author'],
        thread_data['op']['content'],
        thread_data['op']['timestamp'],
        json.dumps(thread_data['op'].get('attachment')) if thread_data['op'].get('attachment') else None
    ))
    
    conn.commit()
    conn.close()

def get_forum_threads():
    """Get all forum threads with their replies"""
    conn = get_db()
    c = conn.cursor()
    
    # Get all threads
    threads = c.execute('SELECT * FROM forum_threads').fetchall()
    
    # Get replies for each thread
    for thread in threads:
        replies = c.execute(
            'SELECT * FROM forum_replies WHERE thread_id = ? ORDER BY timestamp',
            (thread['thread_id'],)
        ).fetchall()
        
        # Convert attachment JSON strings back to dictionaries
        if thread['op_attachment']:
            thread['op_attachment'] = json.loads(thread['op_attachment'])
        
        # Restructure thread to match original format
        thread['threadId'] = thread['thread_id']
        thread['op'] = {
            'author': thread['op_author'],
            'content': thread['op_content'],
            'timestamp': thread['op_timestamp'],
        }
        if thread['op_attachment']:
            thread['op']['attachment'] = thread['op_attachment']
            
        thread['replies'] = replies
        
        # Clean up raw database fields
        del thread['thread_id']
        del thread['op_author']
        del thread['op_content']
        del thread['op_timestamp']
        del thread['op_attachment']
    
    conn.close()
    return threads

def save_forum_reply(thread_id, reply_data):
    """Save a forum reply to the database"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO forum_replies (thread_id, author, content, timestamp, attachment)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        thread_id,
        reply_data['author'],
        reply_data['content'],
        reply_data['timestamp'],
        json.dumps(reply_data.get('attachment')) if reply_data.get('attachment') else None
    ))
    
    conn.commit()
    conn.close()

def save_chat_message(message_data):
    """Save a chat message to the database"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO chat_messages (sender, message, timestamp)
        VALUES (?, ?, ?)
    ''', (
        message_data['sender'],
        message_data['message'],
        message_data['timestamp']
    ))
    
    conn.commit()
    conn.close()

def get_chat_messages(limit=None):
    """Get chat messages, optionally limited to N most recent"""
    conn = get_db()
    c = conn.cursor()
    
    if limit:
        messages = c.execute(
            'SELECT * FROM chat_messages ORDER BY timestamp DESC LIMIT ?',
            (limit,)
        ).fetchall()
    else:
        messages = c.execute('SELECT * FROM chat_messages ORDER BY timestamp').fetchall()
    
    conn.close()
    return messages

def save_agent(agent_data):
    """Save or update an agent in the database"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        INSERT OR REPLACE INTO agents 
        (agent_id, name, persona, thoughts, activity, left, joined_at, left_timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        agent_data.get('id'),
        agent_data.get('name'),
        agent_data.get('persona'),
        json.dumps(agent_data.get('thoughts', [])),
        json.dumps(agent_data.get('activity', [])),
        agent_data.get('left', False),
        agent_data.get('joinedAt'),
        agent_data.get('leftTimestamp')
    ))
    
    conn.commit()
    conn.close()

def get_agents(active_only=True):
    """Get all agents, optionally filtering to only active ones"""
    conn = get_db()
    c = conn.cursor()
    
    if active_only:
        agents = c.execute('SELECT * FROM agents WHERE left = 0').fetchall()
    else:
        agents = c.execute('SELECT * FROM agents').fetchall()
    
    # Convert JSON strings back to lists
    for agent in agents:
        agent['thoughts'] = json.loads(agent['thoughts']) if agent['thoughts'] else []
        agent['activity'] = json.loads(agent['activity']) if agent['activity'] else []
        agent['id'] = agent['agent_id']
        agent['joinedAt'] = agent['joined_at']
        agent['leftTimestamp'] = agent['left_timestamp']
        
        # Clean up raw database fields
        del agent['agent_id']
        del agent['joined_at']
        del agent['left_timestamp']
    
    conn.close()
    return agents

# Initialize database when module is imported
init_db() 