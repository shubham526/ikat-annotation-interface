import argparse
import json
import os
import sqlite3
import sys


def create_schema(data_dir):
    # Connect to SQLite database (will create if it doesn't exist)
    conn = sqlite3.connect('ikat-database.db')
    cursor = conn.cursor()

    # Create conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            conversation_context TEXT,  
            turn_id TEXT,
            run_id TEXT,
            response TEXT
        )
    ''')

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            password TEXT
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

    # Create batches table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS batches (
            batch_id INTEGER PRIMARY KEY
        )
    ''')

    # Create batch_conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS batch_conversations (
            batch_id INTEGER,
            conversation_id TEXT,
            FOREIGN KEY (batch_id) REFERENCES batches (batch_id),
            FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
        )
    ''')

    # Create batch_assignments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS batch_assignments (
            user_id TEXT NOT NULL,
            batch_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (batch_id) REFERENCES batches (batch_id)
        )
    ''')

    # Insert conversations and batches into tables
    batch_files = [f for f in os.listdir(data_dir) if f.startswith('batch_') and f.endswith('.json')]
    for batch_file in batch_files:
        with open(os.path.join(data_dir, batch_file), 'r') as f:
            batch_data = json.load(f)
            cursor.execute('INSERT INTO batches DEFAULT VALUES')  # Insert a new batch and get its ID
            batch_id = cursor.lastrowid
            for item in batch_data:
                # Insert conversation if it doesn't exist
                # Insert conversation if it doesn't exist
                cursor.execute('''
                        INSERT OR IGNORE INTO conversations (conversation_id, conversation_context, turn_id, run_id, response) VALUES (?, ?, ?, ?, ?)
                    ''', (item['conversation_id'], item['conversation_context'], item['turn_id'], item['run_id'], item['response']))
                # Map the conversation to the batch
                cursor.execute('''
                    INSERT INTO batch_conversations (batch_id, conversation_id) VALUES (?, ?)
                ''', (batch_id, item['conversation_id']))

    # Commit changes and close the connection
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser("Create the database schema.")
    parser.add_argument("--data", help='Directory containing data.', required=True)
    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])
    create_schema(args.data)


if __name__ == '__main__':
    main()
