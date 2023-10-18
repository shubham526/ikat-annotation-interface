import sqlite3
import json

# Connect to SQLite database (will create if it doesn't exist)
conn = sqlite3.connect('ikat-database.db')
cursor = conn.cursor()

# Create conversations table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        conversation_id TEXT PRIMARY KEY,
        conversation_context TEXT,  
        turn_id TEXT
    )
''')

# Create users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        password TEXT, 
        is_admin INTEGER DEFAULT 0
    )
''')

# Create evaluations table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS evaluations (
        evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        conversation_id TEXT,
        relevance INTEGER,
        naturalness INTEGER,
        conciseness INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id)
    )
''')

# Insert conversations into table
with open('data.json', 'r') as f:
    data = json.load(f)

for item in data:
    cursor.execute('''
        INSERT OR IGNORE INTO conversations (conversation_id, conversation_context, turn_id) VALUES (?, ?, ?)
    ''', (item['question_id'], item['conversation_context'], item['turn_id']))

# Commit changes and close the connection
conn.commit()
conn.close()

