# pages/Migrate_DB.py
import streamlit as st
import sqlite3, hashlib, os, shutil
from datetime import datetime

st.title("🔑 Database Password Migration")

DB_PATH = "school.db"

if st.button("Run Migration"):
    if os.path.exists(DB_PATH):
        backup_name = f"school_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(DB_PATH, backup_name)
        st.success(f"✅ Backup created: {backup_name}")
    else:
        st.error("❌ Database file not found!")
        st.stop()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT rowid, password FROM users")
    users = cur.fetchall()
    updated_count = 0

    for rowid, password in users:
        # Detect if already hashed
        if len(password) == 64 and all(c in "0123456789abcdef" for c in password.lower()):
            continue
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        cur.execute("UPDATE users SET password=? WHERE rowid=?", (hashed_pw, rowid))
        updated_count += 1

    conn.commit()
    conn.close()

    st.success(f"✅ Migration complete. {updated_count} password(s) updated to SHA-256 hash.")
    st.info("💡 You can now log in using the same passwords with the new login system.")
