import sqlite3

DB_PATH = "data/school.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def add_user(student_id, student_name, email, password_hash, role, class_name, section):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users(student_id, student_name, email, password, role, class, section)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (student_id, student_name, email, password_hash, role, class_name, section))
    conn.commit()
    conn.close()

def add_mark(student_id, subject, marks, submitted_by, class_name, section):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO marks(student_id, subject, marks, class, section, submitted_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, subject, marks, class_name, section, submitted_by))
    conn.commit()
    conn.close()

def fetch_marks_for_student(student_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT subject, marks, class, section, timestamp FROM marks WHERE student_id=?", (student_id,))
    data = cur.fetchall()
    conn.close()
    return data

def fetch_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT student_id, student_name, email, role, class, section FROM users")
    data = cur.fetchall()
    conn.close()
    return data
