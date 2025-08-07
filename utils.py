# utils.py
import requests

# Example function for sending WhatsApp marks notification
def send_whatsapp_mark(student_email, subject, marks):
    # Replace with actual WhatsApp API (Twilio or Gupshup)
    print(f"📲 WhatsApp to {student_email}: Your mark in {subject} is {marks}")

def send_whatsapp_notice(title, message):
    # Broadcast to all students (example)
    print(f"📲 WhatsApp Broadcast: {title} - {message}")
