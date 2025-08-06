import sqlite3
import hashlib
import os
import shutil
from datetime import datetime

DB_PATH = "school.db"  # Change if your DB has a different name

# 1️⃣ Backup existing DB
if os.path.exists(DB_PATH):
    backup_name = f"school_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy(DB_PATH, backup_name)
    print(f"✅ Backup created: {backup_name}")
else:
    print("❌ Database file not found. Make sure DB exists first.")
    exit()

# 2️⃣ Connect to DB
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 3️⃣ Check users table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if not cur.fetchone():
    print("❌ 'users' table not found in DB. Exiting.")
    conn.close()
    exit()

# 4️⃣ Fetch all users
cur.execute("SELECT rowid, email, student_id, password FROM users")
users = cur.fetchall()

updated_count = 0
for rowid, email, student_id, password in users:
    # Detect if password already SHA-256 (64 hex chars)
    if len(password) == 64 and all(c in "0123456789abcdef" for c in password.lower()):
        continue  # Already hashed
    
    # Hash the password
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    cur.execute("UPDATE users SET password=? WHERE rowid=?", (hashed_pw, rowid))
    updated_count += 1

conn.commit()
conn.close()

print(f"✅ Migration complete. {updated_count} password(s) updated to SHA-256 hash.")
print("💡 You can now log in using the same passwords with the new login system.")
