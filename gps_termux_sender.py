
"""
Send LIVE GPS from an Android phone running Termux + termux-api.
Requires: termux-api app installed, and "pkg install termux-api python requests"
Usage:
    export API_TOKEN=osnarayana
    python gps_termux_sender.py --endpoint http://<server-ip>:5055/update_gps --student 1 --interval 10
"""
import argparse, json, os, subprocess, time
import requests

def get_termux_location(provider="gps", timeout=20):
    # Runs: termux-location --provider gps --request once --timeout 20
    cmd = ["termux-location", "--provider", provider, "--request", "once", "--timeout", str(timeout)]
    out = subprocess.check_output(cmd, text=True)
    j = json.loads(out)
    return float(j["latitude"]), float(j["longitude"])

def send(endpoint, token, student_id, lat, lon):
    headers = {"X-API-Token": token}
    data = {"fk_student_id": str(student_id), "lat": str(lat), "lon": str(lon)}
    r = requests.post(endpoint, headers=headers, data=data, timeout=15)
    r.raise_for_status()
    return r.json()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True, help="e.g. http://192.168.1.35:5055/update_gps")
    ap.add_argument("--student", default="1")
    ap.add_argument("--interval", type=int, default=10, help="seconds between sends")
    ap.add_argument("--provider", default="gps", choices=["gps", "network", "passive"])
    args = ap.parse_args()

    token = os.environ.get("API_TOKEN", "osnarayana")
    print(f"Sending to {args.endpoint} every {args.interval}s as student={args.student}")
    while True:
        try:
            lat, lon = get_termux_location(provider=args.provider)
            j = send(args.endpoint, token, args.student, lat, lon)
            print(f"Sent {lat:.6f},{lon:.6f} -> ok={j.get('ok')}")
        except Exception as e:
            print("Error:", e)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
