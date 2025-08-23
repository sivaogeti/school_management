
import os
from datetime import datetime
from flask import Flask, request, jsonify

#TOKEN = os.environ.get("API_TOKEN", "osnarayana")
# --- Config ---
TOKEN = "osnarayana"  # must match the sender
APP = Flask(__name__)

last_points = []  # in-memory log of recent points (most recent first)
MAX_POINTS = 200

from flask import send_from_directory, render_template_string

@APP.get("/send_gps")
def send_gps_page():
    # Serve your existing HTML (must be in the same folder as app.py)
    return send_from_directory(".", "send_gps.html")

# Optional: if your HTML currently posts to a hardcoded IP,
# switch its form/fetch to post to "/update_gps" (relative path),
# so it works behind ngrok without CORS issues.


@APP.route("/update_gps", methods=["POST"])
def update_gps():
    # Auth
    hdr = request.headers.get("X-API-Token", "")
    if hdr != TOKEN:
        return jsonify({"ok": False, "error": "bad token"}), 401

    fk_student_id = request.form.get("fk_student_id")
    lat = request.form.get("lat")
    lon = request.form.get("lon")

    if not (fk_student_id and lat and lon):
        return jsonify({"ok": False, "error": "missing params"}), 400

    try:
        lat = float(lat); lon = float(lon)
    except ValueError:
        return jsonify({"ok": False, "error": "invalid lat/lon"}), 400

    point = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "fk_student_id": fk_student_id,
        "lat": lat,
        "lon": lon,
        "ip": request.remote_addr,
        "ua": request.user_agent.string,
    }
    last_points.insert(0, point)
    if len(last_points) > MAX_POINTS:
        last_points.pop()

    return jsonify({"ok": True, "received": point})

@APP.get("/")
def root():
    if not last_points:
        return "No points yet. POST to /update_gps", 200
    p = last_points[0]
    return f"Last point: id={p['fk_student_id']} @ {p['lat']:.6f},{p['lon']:.6f} at {p['ts']}", 200

@APP.get("/points.json")
def points_json():
    return jsonify(last_points)

if __name__ == "__main__":
    # Bind to 0.0.0.0 so phones on LAN can reach it
    APP.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5055")), debug=True)
