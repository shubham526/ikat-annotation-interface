import sqlite3
import hashlib
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

# Check if the 'admin' user already exists
cursor.execute("SELECT * FROM users WHERE user_id = 'admin'")
admin_exists = cursor.fetchone()

# If 'admin' user doesn't exist, insert it with a hashed password
if not admin_exists:
    # Replace 'Alohomora@ikat2023' with the actual password
    password = 'Alohomora@ikat2023'

    # Hash the password using SHA-256 (you can choose a different hashing algorithm)
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    cursor.execute("INSERT INTO users (user_id, password, is_admin) VALUES (?, ?, ?)",
                   ('admin', password_hash, 1))


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
