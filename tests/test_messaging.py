# tests/test_messaging.py
import os
import sqlite3
import tempfile
import shutil
import pytest
from db import get_connection, init_db
import gupshup_sender

# We'll monkeypatch gupshup_sender.send_gupshup_whatsapp to avoid real HTTP calls.

@pytest.fixture(scope="session")
def temp_db_dir(tmp_path_factory):
    tmpdir = tmp_path_factory.mktemp("school_test")
    db_path = os.path.join(tmpdir, "school.db")
    # create a copy of your production DB or init a fresh DB
    # We'll init fresh
    from db import DB_PATH
    # create new DB file
    shutil.copy(DB_PATH, db_path)
    return db_path

@pytest.fixture(autouse=True)
def use_temp_db(monkeypatch, tmp_path):
    # override DB_PATH used by db.get_connection to use a temp file
    tmp = tmp_path / "school.db"
    # create a fresh DB using db.init_db
    from db import DB_PATH as orig_db_path
    # copy original DB to tmp so seeds exist
    shutil.copy(orig_db_path, tmp)
    monkeypatch.setenv("SCHOOL_DB_PATH", str(tmp))  # optional if your get_connection reads env
    # monkeypatch get_connection to return connection to tmp
    import db
    monkeypatch.setattr(db, "DB_PATH", str(tmp))
    # re-import get_connection to pick up patch
    yield
    # cleanup done by pytest tmp_path

def test_send_in_app_and_whatsapp_inserts(monkeypatch):
    sent = []

    def fake_send(to_number, message, student_id=None):
        sent.append((to_number, message, student_id))
        # simulate logging to whatsapp_logs (gupshup_sender.log_whatsapp will be called by the real flow)
        return True

    monkeypatch.setattr(gupshup_sender, "send_gupshup_whatsapp", fake_send)

    # ensure there is a test student & teacher
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (student_id, student_name, email, password, role, class, section, student_phone, parent_phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("TST001", "Test Student", "tst@student.local", "pw", "Student", "1", "A", "919000000001", "919000000002"))
    cur.execute("INSERT OR IGNORE INTO users (student_id, student_name, email, password, role, class, section) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (None, "Teacher 1", "teacher1@local", "pw", "Teacher", "1", "A"))
    conn.commit()

    # call function under test (teacher -> student message)
    from gupshup_sender import send_in_app_and_whatsapp_to_student
    send_in_app_and_whatsapp_to_student("teacher1@local", "TST001", "Hello from test")

    # verify message stored in messages table
    cur.execute("SELECT sender_email, receiver_email, message FROM messages WHERE sender_email=? ORDER BY timestamp DESC LIMIT 1", ("teacher1@local",))
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "teacher1@local"
    assert "Hello from test" in row[2]

    conn.close()

def test_notify_student_mark_bulk(monkeypatch):
    sent = []
    def fake_send(to_number, message, student_id=None):
        sent.append((to_number, message))
        return True
    monkeypatch.setattr(gupshup_sender, "send_gupshup_whatsapp", fake_send)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (student_id, student_name, email, password, role, class, section, student_phone, parent_phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("TST002", "Student Two", "s2@local", "pw", "Student", "1", "A", "919000000003", "919000000004"))
    conn.commit()

    from gupshup_sender import notify_student_mark_bulk
    notify_student_mark_bulk("TST002", {"Maths": 95, "English": 88})
    # check that fake_send was called at least twice (student + parent)
    assert len(sent) >= 2
    # sample check message includes subject
    assert "Maths" in sent[0][1] or "Maths" in sent[1][1]

    conn.close()
