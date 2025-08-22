import requests
import json

def send_gupshup_whatsapp(destination, text):
    url = "https://api.gupshup.io/wa/api/v1/msg"
    payload = {
        "channel": "whatsapp",
        "source": "917834811114",   # your Gupshup bot number
        "destination": destination,
        "message": json.dumps({"type": "text", "text": text}),
        "src.name": "MRBusinessbot"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "apikey": "hzae5wibtyrailxmx1opl6dzawwgtgbn"
    }

    response = requests.post(url, headers=headers, data=payload)
    print("Status:", response.status_code)
    print("Response:", response.text)

# ---- test call ----
send_gupshup_whatsapp("917989502914", "Hello! This is a message")
