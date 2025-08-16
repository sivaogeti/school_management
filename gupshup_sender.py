import sqlite3
import requests
from db import get_connection
import json 

GUPSHUP_API_KEY = "wquoxqv5af7kdj87parzqdedldwqusl3"
GUPSHUP_SENDER = "917834811114"
GUPSHUP_BOTNAME = "bananashopbot"

def log_whatsapp(student_id, phone, message, status, response):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO whatsapp_logs (student_id, phone_number, message, status, response)
        VALUES (?, ?, ?, ?, ?)
    """, (student_id, phone, message, status, response))
    conn.commit()
    conn.close()

def send_gupshup_whatsapp(to_number: str, message: str, student_id=None):
    """Sends WhatsApp text via Gupshup API and logs it."""
    if not to_number:
        print("❌ No destination number provided for WhatsApp message")
        return False
    
    # Escape quotes for safe JSON
    #safe_message = message.replace('"', '\\"')
    
    payload = {
        "channel": "whatsapp",
        "source": GUPSHUP_SENDER,
        "destination": to_number.replace("+", ""),        
        "message": json.dumps({
            "type": "text",
            "text": message
        }),
        "src.name": GUPSHUP_BOTNAME
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "apikey": GUPSHUP_API_KEY,
        "Cache-Control": "no-cache"
    }

    try:
        response = requests.post("https://api.gupshup.io/wa/api/v1/msg", data=payload, headers=headers)
        try:
            resp_json = response.json()
            api_status = resp_json.get("status", "").lower()
            status = "SUCCESS" if api_status in ["submitted", "success"] else "FAILED"
        except Exception:
            status = "FAILED"
        log_whatsapp(student_id, to_number, message, status, response.text)
        print(f"✅ Gupshup Status: {response.status_code} | {response.text}")
        return status == "SUCCESS"
    except Exception as e:
        log_whatsapp(student_id, to_number, message, "ERROR", str(e))
        print("❌ Error sending WhatsApp:", e)
        return False
        
        
# -----------------------
# NEW: Messaging Feature
# -----------------------
def send_in_app_and_whatsapp(sender_email, receiver_email, message_text):
    """
    Inserts message into DB and sends WhatsApp to the receiver if they have a phone number.
    Works for both students and teachers.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Save in messages table
    cur.execute("""
        INSERT INTO messages (sender_email, receiver_email, message)
        VALUES (?, ?, ?)
    """, (sender_email, receiver_email, message_text))
    conn.commit()

    # Lookup receiver's details
    cur.execute("""
        SELECT student_id, student_phone, parent_phone
        FROM users
        WHERE email=?
    """, (receiver_email,))
    row = cur.fetchone()
    conn.close()

    if row:
        student_id, student_phone, parent_phone = row
        if student_phone:
            send_gupshup_whatsapp(student_phone, message_text, student_id)
        if parent_phone:
            send_gupshup_whatsapp(parent_phone, f"👨‍👩‍👦 Parent Alert: {message_text}", student_id)
    else:
        print(f"❌ No phone details found for {receiver_email}")


def send_in_app_and_whatsapp_to_student(sender_email, student_id, message_text):
    """For teacher sending to student + parent."""
    conn = get_connection()
    cur = conn.cursor()

    # Find student's email + phone
    cur.execute("""
        SELECT email, student_phone, parent_phone
        FROM users
        WHERE student_id=?
    """, (student_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        print(f"❌ Student {student_id} not found")
        return

    student_email, student_phone, parent_phone = row

    # Insert into messages
    cur.execute("""
        INSERT INTO messages (sender_email, receiver_email, message)
        VALUES (?, ?, ?)
    """, (sender_email, student_email, message_text))
    conn.commit()
    conn.close()

    # Send WhatsApp to both
    if student_phone:
        send_gupshup_whatsapp(student_phone, message_text, student_id)
    if parent_phone:
        send_gupshup_whatsapp(parent_phone, f"👨‍👩‍👦 Parent Alert: {message_text}", student_id)


def notify_student_marks_combined(student_id, marks_dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT student_name, student_phone, parent_phone FROM users WHERE student_id=? AND role='Student'",
        (student_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        print(f"❌ Student {student_id} not found for WhatsApp marks notification")
        return
    student_name, student_phone, parent_phone = row
    marks_text = "\n".join([f"{subj}: {mark}" for subj, mark in marks_dict.items()])
    msg = f"📚 Marks Update for {student_name} ({student_id}):\n{marks_text}"
    send_gupshup_whatsapp(student_phone, msg, student_id)
    send_gupshup_whatsapp(parent_phone, f"👨‍👩‍👦 Parent Alert:\n{msg}", student_id)


def notify_student_mark_bulk(student_id: str, marks_dict: dict):
    """
    Send one WhatsApp message with all marks for a student.
    marks_dict = {"Telugu": 30, "Maths": 20, "Hindi": 30}
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT student_name, student_phone, parent_phone FROM users WHERE student_id=? AND role='Student'",
        (student_id,)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        print(f"❌ Student {student_id} not found for WhatsApp bulk marks notification")
        return

    student_name, student_phone, parent_phone = row

    marks_lines = "\n".join([f"{sub}: {score}" for sub, score in marks_dict.items()])
    msg = f"📚 Marks Update for {student_name} ({student_id}):\n{marks_lines}"

    print(f"Sending to Student → {student_id} → {student_phone}")
    send_gupshup_whatsapp(student_phone, msg)

    print(f"Sending to Parent → {student_id} → {parent_phone}")
    send_gupshup_whatsapp(parent_phone, f"👨‍👩‍👦 Parent Alert:\n{msg}")


def notify_attendance(student_id, status, date_str):
    if status != "Absent":
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT student_name, student_phone, parent_phone FROM users WHERE student_id=? AND role='Student'",
        (student_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        print(f"❌ Student {student_id} not found for WhatsApp attendance notification")
        return
    student_name, student_phone, parent_phone = row
    msg = f"📅 Attendance Update for {student_name} ({student_id}): {status} on {date_str}"
    send_gupshup_whatsapp(student_phone, msg, student_id)
    send_gupshup_whatsapp(parent_phone, f"👨‍👩‍👦 Parent Alert: {msg}", student_id)






def notify_fee_payment(student_id: str, amount: float):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT student_name, student_phone, parent_phone FROM users WHERE student_id=? AND role='Student'",
        (student_id,)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        print(f"❌ Student {student_id} not found for WhatsApp payment notification")
        return

    student_name, student_phone, parent_phone = row
    msg = f"💳 Fee Payment Alert: {student_name} ({student_id}) paid ₹{amount:,.2f}. Thank you!"

    print(f"Sending to Student → {student_id} → {student_phone}")
    send_gupshup_whatsapp(student_phone, msg)

    print(f"Sending to Parent → {student_id} → {parent_phone}")
    send_gupshup_whatsapp(parent_phone, f"👨‍👩‍👦 Parent Alert: {msg}")


def broadcast_notice(title: str, message: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT student_id, student_phone, parent_phone FROM users WHERE role='Student'")
    rows = cur.fetchall()
    conn.close()

    full_message = f"📢 School Notice: {title}\n\n{message}"

    for student_id, student_phone, parent_phone in rows:
        send_gupshup_whatsapp(student_phone, full_message)
        send_gupshup_whatsapp(parent_phone, f"👨‍👩‍👦 Parent Alert: {full_message}")
        
def send_file_upload_alert(category, title, class_name=None, section=None):
    conn = get_connection()
    cur = conn.cursor()
    
    
    # Get student & parent numbers
    if class_name and section:
        cur.execute("""
            SELECT student_id, student_phone, parent_phone
            FROM users
            WHERE role='Student' AND class=? AND section=?
        """, (class_name, section))
    else:
        cur.execute("""
            SELECT student_id, student_phone, parent_phone
            FROM users
            WHERE role='Student'
        """)

    rows = cur.fetchall()
    conn.close()

    for sid, sphone, pphone in rows:
        msg = f"📂 New {category} Uploaded: {title}"
        if sphone:
            send_gupshup_whatsapp(sphone, msg, sid)
        if pphone:
            send_gupshup_whatsapp(pphone, f"👨‍👩‍👦 Parent Alert: {msg}", sid)


# -------------------------
# Broadcast helpers for notices / homework / syllabus
# -------------------------
def broadcast_notice_whatsapp(title, message, class_filter=None, section_filter=None):
    """
    Sends a notice message via WhatsApp to all students (or class/section filtered).
    Also logs each send via whatsapp_logs.
    """
    conn = get_connection()
    cur = conn.cursor()
    sql = "SELECT student_id, student_phone, parent_phone FROM users WHERE role='Student'"
    params = []
    if class_filter:
        sql += " AND class=?"
        params.append(class_filter)
    if section_filter:
        sql += " AND section=?"
        params.append(section_filter)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    
    full_message = f"📢 {title}\n\n{message}"
    for student_id, s_phone, p_phone in rows:
        if s_phone:
            send_gupshup_whatsapp(s_phone, full_message, student_id)
        if p_phone:
            send_gupshup_whatsapp(p_phone, f"👨‍👩‍👦 Parent Alert:\n{full_message}", student_id)

def send_notice_whatsapp_to_class(class_name, section, title, message):
    """
    Send a notice via WhatsApp to all students & parents in the specified class/section.
    If class_name or section is None, send to ALL users.
    """
    conn = get_connection()
    cur = conn.cursor()

    if class_name and section:
        cur.execute("""
            SELECT student_id, student_phone, parent_phone
            FROM users
            WHERE role='Student' AND class=? AND section=?
        """, (class_name, section))
    else:
        cur.execute("""
            SELECT student_id, student_phone, parent_phone
            FROM users
            WHERE role='Student'
        """)

    recipients = cur.fetchall()
    conn.close()

    if not recipients:
        return

    for sid, sphone, pphone in recipients:
        text = f"📢 School Notice: {title}\n\n{message}"
        if sphone:
            send_gupshup_whatsapp(sphone, text, sid)
        if pphone:
            send_gupshup_whatsapp(pphone, text, sid)



if __name__ == "__main__":
    notify_student_mark("STU001", "Mathematics", 95)
    broadcast_notice("Sports Day", "The annual sports day will be held on 15th Aug at 9AM.")
    notify_fee_payment("STU001", 2000.00)
    notify_attendance("STU001", "Absent", "2025-08-08")
