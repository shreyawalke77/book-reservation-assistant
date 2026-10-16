import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), 'library.db')

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Books catalogue table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS books (
        book_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT NOT NULL,
        isbn TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Available', 'Reserved', 'Issued', 'Reference Only')),
        shelf_location TEXT NOT NULL,
        description TEXT,
        tags TEXT
    )
    ''')

    # Reservations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reservations (
        reservation_id TEXT PRIMARY KEY,
        user_name TEXT NOT NULL,
        student_id TEXT NOT NULL,
        book_id TEXT NOT NULL,
        book_title TEXT NOT NULL,
        reservation_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Active', 'Fulfilled', 'Cancelled')),
        created_at TEXT NOT NULL,
        FOREIGN KEY (book_id) REFERENCES books (book_id)
    )
    ''')

    # Seed books if empty
    cursor.execute('SELECT COUNT(*) as count FROM books')
    count = cursor.fetchone()['count']
    if count == 0:
        seed_books = [
            (
                'BK-101', 'Artificial Intelligence: A Modern Approach',
                'Stuart Russell & Peter Norvig', 'Computer Science',
                '978-0134610993', 'Available', 'Rack A-12',
                'Comprehensive guide to modern AI, covering search algorithms, knowledge representation, probabilistic reasoning, and machine learning.',
                'ai, machine learning, modern approach, search algorithms, beginner, advanced'
            ),
            (
                'BK-102', 'Clean Code: A Handbook of Agile Software Craftsmanship',
                'Robert C. Martin', 'Software Engineering',
                '978-0132350884', 'Available', 'Rack B-04',
                'Best practices for writing clean, maintainable, readable, and professional software.',
                'clean code, software craftsmanship, best practices, refactoring, agile'
            ),
            (
                'BK-103', 'Introduction to Algorithms (CLRS)',
                'Thomas H. Cormen et al.', 'Computer Science',
                '978-0262033848', 'Reserved', 'Rack A-08',
                'The authoritative handbook covering design and analysis of algorithms, data structures, and graph theory.',
                'algorithms, clrs, data structures, sorting, graphs, dynamic programming'
            ),
            (
                'BK-104', 'Deep Learning',
                'Ian Goodfellow, Yoshua Bengio, Aaron Courville', 'Artificial Intelligence',
                '978-0262035613', 'Available', 'Rack A-15',
                'Mathematical foundations of neural networks, convolutional networks, recurrent architectures, and generative modeling.',
                'deep learning, neural networks, goodfellow, ml, computer vision, nlp'
            ),
            (
                'BK-105', 'Design Patterns: Elements of Reusable Object-Oriented Software',
                'Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides', 'Software Engineering',
                '978-0201633610', 'Available', 'Rack B-02',
                'The classic Gang of Four guide to reusable software architectures and design patterns.',
                'design patterns, oop, gang of four, software architecture, creational, structural'
            ),
            (
                'BK-106', 'Database System Concepts',
                'Abraham Silberschatz, Henry Korth, S. Sudarshan', 'Databases',
                '978-0078022159', 'Available', 'Rack C-07',
                'Core principles of database architectures, relational algebra, SQL, indexing, and transaction management.',
                'database, sql, silberschatz, relational, indexing, acid'
            ),
            (
                'BK-107', 'Computer Networking: A Top-Down Approach',
                'James Kurose & Keith Ross', 'Networking',
                '978-0133594140', 'Issued', 'Rack D-03',
                'Structured exploration of networking from application layer protocols to physical layer transmissions.',
                'networking, kurose, tcp/ip, protocols, sockets, routing'
            ),
            (
                'BK-108', 'Python Crash Course',
                'Eric Matthes', 'Programming',
                '978-1593279288', 'Available', 'Rack B-10',
                'A hands-on, project-based introduction to programming with Python for beginners.',
                'python, crash course, programming, beginners, scripting'
            ),
            (
                'BK-109', 'Operating System Concepts (Dinosaur Book)',
                'Abraham Silberschatz, Peter B. Galvin, Greg Gagne', 'Systems',
                '978-1119800361', 'Available', 'Rack C-12',
                'Foundational study of process scheduling, synchronization, memory paging, and file storage.',
                'operating systems, os, processes, threads, memory management, deadlock'
            ),
            (
                'BK-110', 'Designing Data-Intensive Applications',
                'Martin Kleppmann', 'Distributed Systems',
                '978-1449373320', 'Available', 'Rack C-19',
                'The definitive guide to reliability, scalability, and maintainability in large-scale modern distributed systems.',
                'distributed systems, data intensive, kleppmann, scalability, replication, partitioning'
            ),
            (
                'BK-111', 'The Pragmatic Programmer',
                'David Thomas & Andrew Hunt', 'Software Engineering',
                '978-0135957059', 'Available', 'Rack B-08',
                'Essential career and architectural advice for turning software development into craftsmanship.',
                'pragmatic programmer, career, best practices, debugging, craftsmanship'
            ),
            (
                'BK-112', 'Speech and Language Processing',
                'Daniel Jurafsky & James H. Martin', 'Artificial Intelligence',
                '978-0131873216', 'Reserved', 'Rack A-22',
                'Comprehensive textbook covering natural language processing, speech recognition, and language models.',
                'nlp, natural language processing, speech, jurafsky, transformers, llm'
            )
        ]
        cursor.executemany('''
            INSERT INTO books (book_id, title, author, category, isbn, status, shelf_location, description, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', seed_books)

        # Seed an existing sample reservation for testing status and cancellation
        cursor.execute('''
            INSERT INTO reservations (reservation_id, user_name, student_id, book_id, book_title, reservation_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('RES-2026-1030', 'Aarav Sharma', 'STU-4081', 'BK-103', 'Introduction to Algorithms (CLRS)', '2026-10-18', 'Active', '2026-10-12 14:30:00'))

    conn.commit()
    conn.close()

# Helper queries
def query_books(search_text=None, category=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM books WHERE 1=1"
    params = []
    
    if category:
        query += " AND LOWER(category) LIKE ?"
        params.append(f"%{category.lower()}%")
        
    if search_text:
        search_like = f"%{search_text.lower()}%"
        query += " AND (LOWER(title) LIKE ? OR LOWER(author) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(description) LIKE ?)"
        params.extend([search_like, search_like, search_like, search_like])
        
    cursor.execute(query, params)
    books = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return books

def get_book_by_id_or_title(identifier):
    conn = get_connection()
    cursor = conn.cursor()
    ident = identifier.strip().lower()
    
    # Try exact book_id first
    cursor.execute("SELECT * FROM books WHERE LOWER(book_id) = ?", (ident,))
    row = cursor.fetchone()
    
    # Try exact title
    if not row:
        cursor.execute("SELECT * FROM books WHERE LOWER(title) = ?", (ident,))
        row = cursor.fetchone()
        
    # Try fuzzy title match
    if not row:
        cursor.execute("SELECT * FROM books WHERE LOWER(title) LIKE ?", (f"%{ident}%",))
        row = cursor.fetchone()

    conn.close()
    return dict(row) if row else None

def get_all_books():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books ORDER BY book_id ASC")
    books = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return books

def insert_reservation(res_id, user_name, student_id, book_id, book_title, res_date):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Update book status to Reserved
    cursor.execute("UPDATE books SET status = 'Reserved' WHERE book_id = ?", (book_id,))
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO reservations (reservation_id, user_name, student_id, book_id, book_title, reservation_date, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Active', ?)
    ''', (res_id, user_name, student_id, book_id, book_title, res_date, now_str))
    
    conn.commit()
    conn.close()
    return True

def get_reservation(res_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reservations WHERE UPPER(reservation_id) = ?", (res_id.strip().upper(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_reservations():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reservations ORDER BY created_at DESC")
    reservations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return reservations

def cancel_reservation_record(res_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reservations WHERE UPPER(reservation_id) = ?", (res_id.strip().upper(),))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "Reservation reference not found."
    
    res = dict(row)
    if res['status'] == 'Cancelled':
        conn.close()
        return False, "This reservation has already been cancelled previously."
        
    # Set reservation to Cancelled
    cursor.execute("UPDATE reservations SET status = 'Cancelled' WHERE UPPER(reservation_id) = ?", (res_id.strip().upper(),))
    # Revert book status to Available if currently reserved
    cursor.execute("UPDATE books SET status = 'Available' WHERE book_id = ?", (res['book_id'],))
    
    conn.commit()
    conn.close()
    return True, f"Reservation {res_id.upper()} for '{res['book_title']}' has been successfully cancelled and the book is now marked Available."
