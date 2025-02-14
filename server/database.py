import sqlite3
from datetime import datetime
import json
import os

# Database initialization
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'app.db')

def init_db():
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create tables
    c.executescript('''
        CREATE TABLE IF NOT EXISTS forum_threads (
            thread_id TEXT PRIMARY KEY,
            op_author TEXT NOT NULL,
            op_content TEXT NOT NULL,
            op_timestamp TEXT NOT NULL,
            op_attachment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS forum_replies (
            reply_id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            attachment TEXT,
            FOREIGN KEY (thread_id) REFERENCES forum_threads(thread_id)
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id TEXT PRIMARY KEY,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            persona TEXT,
            thoughts TEXT,
            activity TEXT,
            left BOOLEAN DEFAULT FALSE,
            left_timestamp TEXT,
            joined_at TEXT NOT NULL
        );
    ''')
    
    conn.commit()
    conn.close()
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn

# Forum functions
def get_forum_threads():
    conn = get_db()
    c = conn.cursor()
    
    # Get all threads with their replies
    threads = []
    c.execute('''
        SELECT * FROM forum_threads 
        ORDER BY op_timestamp DESC
    ''')
    
    for thread in c.fetchall():
        thread_data = {
            'threadId': thread['thread_id'],
            'op': {
                'author': thread['op_author'],
                'content': thread['op_content'],
                'timestamp': thread['op_timestamp']
            },
            'replies': []
        }
        
        # Add attachment if exists
        if thread['op_attachment']:
            thread_data['op']['attachment'] = json.loads(thread['op_attachment'])
        
        # Get replies for this thread
        c.execute('''
            SELECT * FROM forum_replies 
            WHERE thread_id = ? 
            ORDER BY timestamp DESC
        ''', (thread['thread_id'],))
        
        replies = c.fetchall()
        for reply in replies:
            reply_data = {
                'author': reply['author'],
                'content': reply['content'],
                'timestamp': reply['timestamp']
            }
            if reply['attachment']:
                reply_data['attachment'] = json.loads(reply['attachment'])
            thread_data['replies'].append(reply_data)
        
        threads.append(thread_data)
    
    conn.close()
    return threads

def save_forum_thread(thread_data):
    conn = get_db()
    c = conn.cursor()
    
    attachment_json = None
    if 'attachment' in thread_data['op']:
        attachment_json = json.dumps(thread_data['op']['attachment'])
    
    c.execute('''
        INSERT INTO forum_threads 
        (thread_id, op_author, op_content, op_timestamp, op_attachment)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        thread_data['threadId'],
        thread_data['op']['author'],
        thread_data['op']['content'],
        thread_data['op']['timestamp'],
        attachment_json
    ))
    
    conn.commit()
    conn.close()

def save_forum_reply(thread_id, reply_data):
    conn = get_db()
    c = conn.cursor()
    
    attachment_json = None
    if 'attachment' in reply_data:
        attachment_json = json.dumps(reply_data['attachment'])
    
    c.execute('''
        INSERT INTO forum_replies 
        (reply_id, thread_id, author, content, timestamp, attachment)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        str(uuid.uuid4()),
        thread_id,
        reply_data['author'],
        reply_data['content'],
        reply_data['timestamp'],
        attachment_json
    ))
    
    conn.commit()
    conn.close()

# Chat functions
def get_chat_messages():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT sender, message, timestamp 
        FROM chat_messages 
        ORDER BY timestamp ASC
    ''')
    
    messages = [{
        'sender': msg['sender'],
        'message': msg['message'],
        'timestamp': msg['timestamp']
    } for msg in c.fetchall()]
    
    conn.close()
    return messages

def save_chat_message(message_data):
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO chat_messages 
        (message_id, sender, message, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (
        str(uuid.uuid4()),
        message_data['sender'],
        message_data['message'],
        message_data['timestamp']
    ))
    
    conn.commit()
    conn.close()

# Agent functions
def get_agents(include_left=False):
    conn = get_db()
    c = conn.cursor()
    
    query = 'SELECT * FROM agents'
    if not include_left:
        query += ' WHERE left = 0'
    
    c.execute(query)
    
    agents = []
    for agent in c.fetchall():
        agent_data = {
            'id': agent['agent_id'],
            'name': agent['name'],
            'persona': agent['persona'],
            'thoughts': json.loads(agent['thoughts']) if agent['thoughts'] else [],
            'activity': json.loads(agent['activity']) if agent['activity'] else [],
            'left': bool(agent['left']),
            'joinedAt': agent['joined_at']
        }
        if agent['left_timestamp']:
            agent_data['leftTimestamp'] = agent['left_timestamp']
        agents.append(agent_data)
    
    conn.close()
    return agents

def save_agent(agent_data):
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        INSERT OR REPLACE INTO agents 
        (agent_id, name, persona, thoughts, activity, left, left_timestamp, joined_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        agent_data['id'],
        agent_data['name'],
        agent_data.get('persona'),
        json.dumps(agent_data.get('thoughts', [])),
        json.dumps(agent_data.get('activity', [])),
        agent_data.get('left', False),
        agent_data.get('leftTimestamp'),
        agent_data.get('joinedAt', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ))
    
    conn.commit()
    conn.close() 