"""
Flask Web Application for Book Reservation Assistant
Serves the chat interface, API endpoints, and live catalogue synchronizer.
"""

from flask import Flask, render_template, request, jsonify
from database import init_db, get_all_books, get_all_reservations
from agent import agent_instance
import uuid

app = Flask(__name__)

# Initialize SQLite database on startup
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    session_id = data.get('session_id')
    
    if not session_id:
        session_id = str(uuid.uuid4())
        
    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    response = agent_instance.process_message(session_id, message)
    response['session_id'] = session_id
    return jsonify(response)

@app.route('/api/books', methods=['GET'])
def get_books():
    books = get_all_books()
    return jsonify({'books': books})

@app.route('/api/reservations', methods=['GET'])
def get_reservations():
    reservations = get_all_reservations()
    return jsonify({'reservations': reservations})

@app.route('/api/reset', methods=['POST'])
def reset_demo():
    # Helper to re-seed demo data if user wants to reset tests
    import os
    from database import DB_FILE
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()
    agent_instance.sessions.clear()
    return jsonify({'success': True, 'message': 'Database re-initialized to initial demo state.'})

if __name__ == '__main__':
    print("==================================================")
    print(" 📚 Book Reservation Assistant - Server Running")
    print(" Web Interface: http://127.0.0.1:5000")
    print(" Non-Blue Academic Theme: Forest Green & Warm Amber")
    print("==================================================")
    app.run(host='127.0.0.1', port=5000, debug=True)
