from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
import hashlib
import os

app = Flask(__name__)
# app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.secret_key = '5538c01ccd1b985692c3669c6fe5f2b2'
ITEMS_PER_PAGE = 1

# for pilot study. if True, remove batch selection logic and
# assign SINGLE_BATCH_ID to every user
SINGLE_BATCH_MODE = False

# when SINGLE_BATCH_ID is True, every user will be assigned
# to this batch ID
SINGLE_BATCH_ID = 1

def insert_evaluation_result(user_id, conversation_id, relevance, completeness,
                             relevance_feedback, completeness_feedback):
    conn = sqlite3.connect('ikat-database.db')
    cursor = conn.cursor()

    # Insert a new evaluation into the evaluations table
    sql_evaluation = '''
        INSERT INTO evaluations (user_id, conversation_id, relevance, completeness, relevance_feedback, completeness_feedback)
        VALUES (?, ?, ?, ?, ?, ?);
    '''
    cursor.execute(sql_evaluation, (user_id, conversation_id, relevance, completeness,
                                    relevance_feedback,
                                    completeness_feedback))

    conn.commit()
    conn.close()


@app.route('/index/<int:page_num>', methods=['GET'])
def index(page_num=1):
    conn = sqlite3.connect('ikat-database.db')
    cursor = conn.cursor()
    print(session)

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # If batch_id is not in session, assign one
    if 'batch_id' not in session:

        if not SINGLE_BATCH_MODE:
            # Count batches the user has already been assigned to
            cursor.execute('''
                SELECT COUNT(batch_id)
                FROM batch_assignments
                WHERE user_id = ?
            ''', (user_id,))
            batch_count = cursor.fetchone()[0]

            # If the user has already been assigned to 2 batches and hasn't decided to continue with more batches
            if batch_count >= 2 and not session.get('continue_with_batches'):
                return redirect(url_for('ask_for_more_batches'))

            # Get a batch that has been assigned to less than 2 users and not assigned to the current user
            cursor.execute('''
                SELECT b.batch_id
                FROM batches b
                LEFT JOIN batch_assignments ba ON b.batch_id = ba.batch_id AND ba.user_id != ?
                WHERE ba.batch_id IS NULL OR ba.user_id != ?
                GROUP BY b.batch_id
                HAVING COUNT(ba.user_id) < 2
                LIMIT 1
            ''', (user_id, user_id))
            batch = cursor.fetchone()

            if not batch:
                # No more batches for the user to evaluate
                return redirect(url_for('no_batches'))

            batch_id = batch[0]
        else:
            print(f'Using single batch mode, assigning ID {SINGLE_BATCH_ID}')
            batch_id = SINGLE_BATCH_ID

        session['batch_id'] = batch_id
        # Clear the continue_with_batches session variable after assigning a new batch
        session.pop('continue_with_batches', None)

        # Assign this batch to the user
        cursor.execute('''
            INSERT INTO batch_assignments (user_id, batch_id)
            VALUES (?, ?)
        ''', (user_id, batch_id))
        conn.commit()

    # Get the conversations for the current batch
    cursor.execute('''
        SELECT conversation_id
        FROM batch_conversations
        WHERE batch_id = ?
        ORDER BY conversation_id
    ''', (session['batch_id'],))

    batch_conversations = [row[0] for row in cursor.fetchall()]

    if page_num > len(batch_conversations):
        return redirect(url_for('thank_you'))

    conversation_id = batch_conversations[page_num - 1]
    cursor.execute('''
        SELECT * FROM conversations WHERE conversation_id = ?
    ''', (conversation_id,))

    rows = cursor.fetchall()
    data = []
    for row in rows:
        conversation_context = row[1]
        response = row[4]

        # replace the labels with HTML versions
        conversation_context = conversation_context.replace("USER: ", "<br><strong>USER: </strong>")
        conversation_context = conversation_context.replace("SYSTEM:", "<br><strong>SYSTEM: </strong>")

        # split into utterances and strip whitespace
        context_utterances = list(map(str.strip, conversation_context.split("\n")))

        # if there are more than 4 utterances, display the first and the last 3
        if len(context_utterances) > 4:
            first_utterance = context_utterances[0]
            final_utterances = context_utterances[-3:]
            utterances_removed = len(context_utterances) - 4
        else:
            # otherwise display them all
            first_utterance = context_utterances[0]
            final_utterances = context_utterances[1:]
            utterances_removed = 0

        data.append({
            'question_id': row[0],
            'batch_id': session['batch_id'],
            'first_utterance' : first_utterance,
            'final_utterances': final_utterances,
            'utterances_removed' : utterances_removed,
            'turn_id': row[2],
            'run_id': row[3],
            'response': response
        })
    conn.close()

    next_page = page_num + 1 if page_num < len(batch_conversations) else None
    prev_page = page_num - 1 if page_num > 1 else None
    is_last_page = False if next_page else True

    return render_template(
        'index.html',
        data=data,
        next_page=next_page,
        prev_page=prev_page,
        show_rubric=True,
        show_examples=True,
        is_last_page=is_last_page,
        progress=f"You are on entry number {page_num} of {len(batch_conversations)}"
    )


@app.route('/evaluate', methods=['POST'])
def evaluate():
    if 'user_id' not in session:
        return jsonify({"message": "You must be logged in to evaluate."}), 403

    user_id = session['user_id']
    data = request.json  # This parses the request body as JSON.
    item_id = data['id']
    if not item_id:
        return jsonify({"message": "Error: 'id' is missing"}), 400

    try:
        relevance = data['relevance']
        completeness = data['completeness']
        relevance_feedback = data['relevance_feedback']
        completeness_feedback = data['completeness_feedback']
    except KeyError:
        return jsonify({"message": "Error: value does not exist"}), 400

    # Attempt to convert relevance, naturalness, and conciseness to integers
    try:
        relevance = int(relevance)
        completeness = int(completeness)
    except ValueError:
        return jsonify({"message": "Error: Invalid integer values"}), 400

    # Check if relevance, naturalness, conciseness, and completeness are within the valid range
    valid_range = (-1, 3)  # Updated to include -1
    if not valid_range[0] <= relevance <= valid_range[1] or not valid_range[0] <= completeness <= valid_range[1]:
        return jsonify({"message": "Error: Values out of range (-1 to 3)"}), 400  # Updated range in the message

    # Insert the evaluation result into the database
    insert_evaluation_result(user_id, item_id, relevance, completeness,
                             relevance_feedback, completeness_feedback)
    return jsonify({"message": "Success"})


@app.route('/ask_for_more_batches', methods=['GET', 'POST'])
def ask_for_more_batches():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # User has decided to continue with more batches
        session['continue_with_batches'] = True  # Set the session variable
        session.pop('batch_id', None)  # Remove the current batch_id from the session
        return redirect(url_for('index', page_num=1))  # Redirect to the index route to get the next batch

    return render_template('ask_for_more_batches.html')


@app.route('/intro', methods=['GET'])
def intro():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('intro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    print(f'session in login:{session}')
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        conn = sqlite3.connect('ikat-database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Verify the entered password against the hashed password
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if user[1] == hashed_password:  # Check password for admin or allow non-admin
                session['user_id'] = user[0]
                return redirect(url_for('intro'))

        flash('Invalid credentials', 'error')  # Flash the error message

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')  # Flash a message
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    print(f'session in signup:{session}')
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        # Hash the password using hashlib (similar to the login route)
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect('ikat-database.db')
        cursor = conn.cursor()

        # Check if the user already exists
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            flash('User ID already exists. Please choose a different one.', 'error')  # Flash the error message
            return redirect(url_for('signup'))

        # Insert the new user into the database
        cursor.execute("INSERT INTO users (user_id, password) VALUES (?, ?)",
                       (user_id, hashed_password))  # Assuming non-admin user

        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html')


@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.route('/thankyou')
def thank_you():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('thank_you.html')

@app.route('/no_batches')
def no_batches():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('no_batches.html')

@app.route('/', methods=['GET'])
def main():
    print(f'session in main: {session}')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
