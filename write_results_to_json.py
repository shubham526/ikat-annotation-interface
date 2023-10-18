import sqlite3
import json
import argparse
import sys


def fetch_data_from_db(database_name):
    # Connect to the SQLite database
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    # Fetch data from the users table
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()

    # Fetch data from the evaluations table
    cursor.execute('SELECT * FROM evaluations')
    evaluations_data = cursor.fetchall()

    conn.close()

    return users, evaluations_data


def organize_data(users, evaluations_data):
    organized_data = []

    for user in users:
        user_id = user[0]
        user_evaluations = []

        for evaluation in evaluations_data:
            _, e_user_id, conversation_id, relevance, naturalness, conciseness = evaluation
            if e_user_id == user_id:
                user_evaluations.append({
                    'conversation_id': conversation_id,
                    'relevance': relevance,
                    'naturalness': naturalness,
                    'conciseness': conciseness
                })

        user_data = {
            'user_id': user_id,
            'evaluations': user_evaluations
        }

        organized_data.append(user_data)

    return organized_data







def write_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


def main():
    parser = argparse.ArgumentParser("Write the evaluation results to a JSON file.")
    parser.add_argument("--database", help='Database file.', required=True)
    parser.add_argument("--save", help='Directory where to save.', required=True)
    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])

    users, evaluations_data = fetch_data_from_db(args.database)
    organized_data = organize_data(users, evaluations_data)
    write_to_json(organized_data, args.save)

    print('Results file written to ==> {}'.format(args.save))


if __name__ == '__main__':
    main()
