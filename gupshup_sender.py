import requests
from db import get_connection, get_student_details
import json 

# 🔑 Replace with your Gupshup credentials
GUPSHUP_API_URL = "https://api.gupshup.io/wa/api/v1/msg"
GUPSHUP_SOURCE = "917834811114"
GUPSHUP_API_KEY = "hzae5wibtyrailxmx1opl6dzawwgtgbn"
GUPSHUP_BOTNAME = "MRBusinessbot"

def send_gupshup_whatsapp(destination, text):
    payload = {
        "channel": "whatsapp",
        "source": GUPSHUP_SOURCE,
        "destination": destination,
        "message": json.dumps({
            "type": "text",
            "text": text
        }),
        "src.name": GUPSHUP_BOTNAME
    }
    headers = {
        "apikey": GUPSHUP_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    r = requests.post(GUPSHUP_API_URL, headers=headers, data=payload)
    print("📨 WhatsApp →", destination, ":", text, f"(status={r.status_code}, resp={r.text})")
    print ("📨 WhatsApp →",":"," Completed")
    return r

# ---------------------------------------------------------
# ATTENDANCE ALERT
# ---------------------------------------------------------
def notify_attendance(student_id, status, date):
    student = get_student_details(student_id)
    if not student:
        return
    msg = f"📆 Attendance Alert: {student['name']} was marked {status} on {date}."
    if student.get("parent_phone"):
        send_gupshup_whatsapp(student["parent_phone"], msg)
        send_gupshup_whatsapp(student["student_phone"], msg)
    elif student.get("student_phone"):
        send_gupshup_whatsapp(student["student_phone"], msg)


def notify_student_marks_bulk(student_id, marks_dict):
    student = get_student_details(student_id)
    if not student:
        return
    marks_text = "\n".join([f"{sub}: {score}" for sub, score in marks_dict.items()])
    msg = f"✏️ Marks Update for {student['name']}:\n{marks_text}"
    if student.get("parent_phone"):
        send_gupshup_whatsapp(student["parent_phone"], msg)
    elif student.get("student_phone"):
        send_gupshup_whatsapp(student["student_phone"], msg)



# ---------------------------------------------------------
# FILE UPLOAD ALERT
# ---------------------------------------------------------
def send_file_upload_alert(file_type, subject, class_name, section):
    """
    Notify parents when Homework/Syllabus/Gallery is uploaded.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT student_name, parent_phone FROM users WHERE role='Student' AND class=? AND section=?",
        (class_name, section),
    )
    rows = cur.fetchall()
    conn.close()

    for name, phone in rows:
        if not phone:
            continue
        msg = f"📢 New {file_type} uploaded for Class {class_name}{section} ({subject})."
        send_gupshup_whatsapp(phone, msg)

def send_in_app_and_whatsapp_to_student(sender_email, student_id, message):
    student = get_student_details(student_id)
    if not student:
        print(f"❌ Student {student_id} not found.")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages(sender_email, receiver_email, message, is_read, timestamp) VALUES (?, ?, ?, 0, datetime('now'))",
        (sender_email, student["email"], message),
    )
    conn.commit()
    conn.close()

    if student.get("parent_phone"):
        send_gupshup_whatsapp(student["parent_phone"], message)
    elif student.get("student_phone"):
        send_gupshup_whatsapp(student["student_phone"], message)

    print(f"✅ Sent in-app + WhatsApp to {student['name']}")


# ---------------------------------------------------------
# IN-APP + WHATSAPP HELPERS
# ---------------------------------------------------------
def send_in_app_and_whatsapp(sender_email, message, receiver_email=None):
    """
    Send in-app message and WhatsApp to a receiver (if phone known).
    """
    conn = get_connection()
    cur = conn.cursor()

    if receiver_email:
        cur.execute(
            "INSERT INTO messages(sender_email, receiver_email, message, is_read, timestamp) VALUES (?, ?, ?, 0, datetime('now'))",
            (sender_email, receiver_email, message),
        )
        conn.commit()

        cur.execute("SELECT parent_phone FROM users WHERE email=?", (receiver_email,))
        row = cur.fetchone()
        if row and row[0]:
            send_gupshup_whatsapp(row[0], message)

    else:
        cur.execute(
            "INSERT INTO messages(sender_email, message, is_read, timestamp) VALUES (?, ?, 0, datetime('now'))",
            (sender_email, message),
        )
        conn.commit()

    conn.close()



