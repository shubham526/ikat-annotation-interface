from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
import hashlib
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
ITEMS_PER_PAGE = 5


def insert_evaluation_result(user_id, conversation_id, relevance, naturalness, conciseness):
    conn = sqlite3.connect('ikat-database.db')
    cursor = conn.cursor()

    # Insert a new evaluation into the evaluations table
    sql_evaluation = '''
        INSERT INTO evaluations (user_id, conversation_id, relevance, naturalness, conciseness)
        VALUES (?, ?, ?, ?, ?);
    '''
    cursor.execute(sql_evaluation, (user_id, conversation_id, relevance, naturalness, conciseness))

    conn.commit()
    conn.close()


@app.route('/index/<int:page_num>', methods=['GET'])
def index(page_num=1):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('ikat-database.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM conversations''')
    data = [{'question_id': row[0], 'conversation_context': row[1]} for row in cursor.fetchall()]
    conn.close()
    start = (page_num - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    data_to_show = data[start:end]
    next_page = page_num + 1 if end < len(data) else None
    prev_page = page_num - 1 if start > 0 else None
    is_last_page = False
    if not next_page:  # Assuming next_page will be None or False if it's the last page
        is_last_page = True

    return render_template(
        'index.html',
        data=data_to_show,
        next_page=next_page,
        prev_page=prev_page,
        show_rubric=True,
        is_last_page=is_last_page
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
        naturalness = data['naturalness']
        conciseness = data['conciseness']
    except KeyError:
        return jsonify({"message": "Error: value does not exist"}), 400

    # Attempt to convert relevance, naturalness, and conciseness to integers
    try:
        relevance = int(relevance)
        naturalness = int(naturalness)
        conciseness = int(conciseness)
    except ValueError:
        return jsonify({"message": "Error: Invalid integer values"}), 400

    # Check if relevance, naturalness, and conciseness are within the valid range
    if not (0 <= relevance <= 3) or not (0 <= naturalness <= 3) or not (0 <= conciseness <= 3):
        return jsonify({"message": "Error: Values out of range (0-3)"}), 400

    # Insert the evaluation result into the database
    insert_evaluation_result(user_id, item_id, relevance, naturalness, conciseness)
    return jsonify({"message": "Success"})


@app.route('/intro', methods=['GET'])
def intro():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('intro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
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
                session['is_admin'] = user[2]
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
        cursor.execute("INSERT INTO users (user_id, password, is_admin) VALUES (?, ?, ?)",
                       (user_id, hashed_password, 0))  # Assuming non-admin user

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


@app.route('/', methods=['GET'])
def main():
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
