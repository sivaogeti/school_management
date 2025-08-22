import sqlite3, hashlib

DB_PATH = '../data/school.db'

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Create tables if not exist
cur.execute('''CREATE TABLE IF NOT EXISTS users(
                    email TEXT PRIMARY KEY,
                    password TEXT,
                    role TEXT)''')
cur.execute('''CREATE TABLE IF NOT EXISTS marks(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_email TEXT,
                    subject TEXT,
                    marks INTEGER,
                    submitted_by TEXT)''')
cur.execute('''CREATE TABLE IF NOT EXISTS notices(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    message TEXT,
                    created_by TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

# Insert admin if not exists
admin_email = "admin@school.com"
admin_pass = hashlib.sha256("admin123".encode()).hexdigest()

cur.execute("SELECT * FROM users WHERE email=?", (admin_email,))
if not cur.fetchone():
    cur.execute("INSERT INTO users VALUES (?,?,?)", (admin_email, admin_pass, "Admin"))
    conn.commit()
    print("✅ Admin user created:", admin_email)
else:
    print("ℹ️ Admin already exists")

# Print all users
print("\nCurrent users in DB:")
for row in cur.execute("SELECT * FROM users"):
    print(row)

conn.close()
