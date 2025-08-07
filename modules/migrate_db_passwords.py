import streamlit as st
import sqlite3, hashlib, os, shutil
from datetime import datetime

st.set_page_config(page_title="🔑 DB Migration", page_icon="🗄️")

st.title("🔑 Database Password Migration Tool")

DB_PATH = "school.db"

st.warning("""
⚠️ **Use this tool only once!**  
This will:
1. Backup your current DB.
2. Convert all plaintext passwords to **SHA-256** for the new login system.
3. Allow old passwords to continue working securely.
""")

if st.button("🚀 Run Migration Now"):
    # 1️⃣ Backup DB
    if os.path.exists(DB_PATH):
        backup_name = f"school_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(DB_PATH, backup_name)
        st.success(f"✅ Backup created: `{backup_name}`")
    else:
        st.error("❌ Database file not found!")
        st.stop()

    # 2️⃣ Connect to DB
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 3️⃣ Fetch all users
    cur.execute("SELECT rowid, password FROM users")
    users = cur.fetchall()

    updated_count = 0
    already_hashed = 0

    # 4️⃣ Hash passwords if not already SHA-256
    for rowid, password in users:
        if not password:
            continue

        # Check if already SHA-256
        if len(password) == 64 and all(c in "0123456789abcdef" for c in password.lower()):
            already_hashed += 1
            continue

        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        cur.execute("UPDATE users SET password=? WHERE rowid=?", (hashed_pw, rowid))
        updated_count += 1

    conn.commit()
    conn.close()

    st.success(f"✅ Migration complete!")
    st.info(f"🔹 {updated_count} password(s) hashed. {already_hashed} were already secure.")

    st.balloons()
    st.write("💡 You can now **log in using the same credentials** with the new system.")
    st.write("🛡️ For security, delete this page after successful migration.")
