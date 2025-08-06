# gupshup_sender.py
import sqlite3
import requests
from db import get_connection

# ======================
# WhatsApp Config
# ======================
GUPSHUP_API_KEY = "wquoxqv5af7kdj87parzqdedldwqusl3"
GUPSHUP_SENDER = "917834811114"
GUPSHUP_BOTNAME = "bananashopbot"


def send_gupshup_whatsapp(to_number: str, message: str):
    if not to_number:
        print("❌ No destination number provided for WhatsApp message")
        return False

    payload = {
        "channel": "whatsapp",
        "source": GUPSHUP_SENDER,
        "destination": to_number.replace("+", ""),
        "message": f'{{"type":"text","text":"{message}"}}',
        "src.name": GUPSHUP_BOTNAME
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "apikey": GUPSHUP_API_KEY,
        "Cache-Control": "no-cache"
    }

    try:
        response = requests.post("https://api.gupshup.io/wa/api/v1/msg", data=payload, headers=headers)
        print(f"✅ Gupshup Status: {response.status_code} | {response.text}")
        return response.status_code == 200
    except Exception as e:
        print("❌ Error sending WhatsApp:", e)
        return False


# ======================
# School Notifications
# ======================
def notify_student_mark(student_id: str, subject: str, marks: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT student_name, student_phone, parent_phone FROM users WHERE student_id=? AND role='Student'",
        (student_id,)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        print(f"❌ Student {student_id} not found for WhatsApp notification")
        return

    student_name, student_phone, parent_phone = row

    msg = f"📚 Marks Update for {student_name} ({student_id}): {subject} = {marks}"
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


from db import get_connection

def notify_attendance(student_id: str, status: str, date_str: str):
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

    print(f"Sending to Student → {student_id} → {student_phone}")
    send_gupshup_whatsapp(student_phone, msg)

    print(f"Sending to Parent → {student_id} → {parent_phone}")
    send_gupshup_whatsapp(parent_phone, f"👨‍👩‍👦 Parent Alert: {msg}")



if __name__ == "__main__":
    notify_student_mark("STU001", "Mathematics", 95)
    broadcast_notice("Sports Day", "The annual sports day will be held on 15th Aug at 9AM.")
