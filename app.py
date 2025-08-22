import streamlit as st
from db import init_db
import hashlib
import json
import razorpay
import os
import base64


# --- GPS receiver (Flask in a background thread) ---
import threading
from flask import Flask, request, jsonify

GPS_API_TOKEN = "osnarayana"   # <-- set your own token
GPS_PORT = 5055                           # <-- open this on firewall if needed

_flask_app = None
_flask_thread = None

def _create_gps_app():
    app = Flask(__name__)

    
    @app.route("/ping")
    def ping():
        return jsonify({"ok": True})

    @app.route("/debug/last")
    def debug_last():
        from db import get_connection
        fk_student_id = request.args.get("fk_student_id", type=int)
        student_id    = request.args.get("student_id", type=int)

        conn = get_connection()
        cur = conn.cursor()
        if fk_student_id:
            cur.execute("SELECT bus_lat, bus_lon FROM student_transport WHERE fk_student_id=?", (fk_student_id,))
        elif student_id:
            cur.execute("SELECT bus_lat, bus_lon FROM student_transport WHERE student_id=?", (student_id,))
        else:
            conn.close()
            return jsonify({"ok": False, "error": "need fk_student_id or student_id"}), 400

        row = cur.fetchone()
        conn.close()
        return jsonify({"ok": True, "bus_lat": row[0] if row else None, "bus_lon": row[1] if row else None})

    @app.route("/update_gps", methods=["POST"])
    def update_gps():
        from db import get_connection  # import here to avoid circulars

        # Simple token check
        if request.headers.get("X-API-Token") != GPS_API_TOKEN:
            return jsonify({"ok": False, "error": "unauthorized"}), 401

        # Accept either fk_student_id (recommended) or student_id (legacy string)
        fk_student_id = request.form.get("fk_student_id")
        legacy_sid    = request.form.get("student_id")
        lat = request.form.get("lat")
        lon = request.form.get("lon")

        try:
            lat = float(lat); lon = float(lon)           
        except Exception:
            return jsonify({"ok": False, "error": "bad lat/lon"}), 400

        if not fk_student_id and not legacy_sid:
            return jsonify({"ok": False, "error": "need fk_student_id or student_id"}), 400

        conn = get_connection()
        cur = conn.cursor()
        
        # after parsing lat/lon and before DB update:
        print(f"[GPS] sid={fk_student_id or legacy_sid} lat={lat} lon={lon}")
        if fk_student_id:
            try:
                fk_student_id = int(fk_student_id)
            except Exception:
                conn.close()
                return jsonify({"ok": False, "error": "fk_student_id must be int"}), 400

            cur.execute("""
                UPDATE student_transport
                   SET bus_lat=?, bus_lon=?
                 WHERE fk_student_id=?
            """, (lat, lon, fk_student_id))
        else:
            # legacy student_id path (INTEGER in your schema; use only if needed)
            try:
                legacy_sid_int = int(legacy_sid)
            except Exception:
                conn.close()
                return jsonify({"ok": False, "error": "student_id must be int"}), 400

            cur.execute("""
                UPDATE student_transport
                   SET bus_lat=?, bus_lon=?
                 WHERE student_id=?
            """, (lat, lon, legacy_sid_int))

        conn.commit()
        conn.close()
        return jsonify({"ok": True})
        
    
    @app.route("/send_gps")
    def send_gps_page():
        return """
<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bus GPS Sender</title>
<h3>Bus GPS Sender</h3><div id="log">Starting…</div>
<script>
  const ENDPOINT = location.origin + "/update_gps";       // same origin (5055)
  const TOKEN = "osnarayana";                              // must match app.py
  const FK_STUDENT_ID = "1";                               // users.id to test

  function log(s){ document.getElementById('log').innerText = s; }

  async function send(lat, lon){
    const fd = new FormData();
    fd.append("fk_student_id", FK_STUDENT_ID);
    fd.append("lat", String(lat));
    fd.append("lon", String(lon));
    const res = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "X-API-Token": TOKEN },
      body: fd
    });
    return res.json();
  }

  function tick(){
    if(!navigator.geolocation){ log("Geolocation not supported."); return; }
    navigator.geolocation.getCurrentPosition(async pos => {
      const {latitude, longitude} = pos.coords;
      try{
        const j = await send(latitude, longitude);
        log(`Sent: ${latitude.toFixed(5)}, ${longitude.toFixed(5)} | ok=${j.ok}`);
      }catch(e){ log("Send failed: " + e); }
    }, err => log("GPS error: " + err.message), { enableHighAccuracy:true, maximumAge:0, timeout:15000 });
  }
  tick(); setInterval(tick, 10000);
</script>
"""


    return app


def start_gps_server_once():
    """Start the Flask GPS receiver in a background thread exactly once."""
    global _flask_app, _flask_thread
    if getattr(start_gps_server_once, "_started", False):
        return
    _flask_app = _create_gps_app()

    # Run Flask in a daemon thread so it doesn't block Streamlit
    _flask_thread = threading.Thread(
        target=_flask_app.run,
        kwargs={"host": "0.0.0.0", "port": GPS_PORT, "debug": False, "use_reloader": False},
        daemon=True,
        name="gps_flask_server"
    )
    _flask_thread.start()
    start_gps_server_once._started = True



# =========================
# 1️⃣ App Config
# =========================
st.set_page_config(page_title="🏫 School Management System", layout="wide")

def apply_student_theme():
    # Locks a light‑green background everywhere after login
    st.markdown("""
    <style>
      :root { --app-bg: #e8f5e9; }

      /* Page & containers */
      html, body { background: var(--app-bg) !important; }
      .stApp { background: var(--app-bg) !important; }
      [data-testid="stAppViewContainer"] { background: var(--app-bg) !important; }
      [data-testid="stSidebar"] { background: var(--app-bg) !important; }

      /* Blocks should be transparent so the page bg shows through */
      .main, .block-container,
      [data-testid="stVerticalBlock"],
      [data-testid="stVerticalBlock"] > div,
      [data-testid="stHorizontalBlock"],
      [data-testid="stHorizontalBlock"] > div {
        background: transparent !important;
      }

      /* Card-like buttons */
      div[data-testid="stButton"] > button {
        background-color: #ffffff !important;
        border: 1px solid #ddd !important;
        border-radius: 12px !important;
        padding: 1.2rem 1rem !important;
        margin: 1rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.08);
        transition: all 0.2s ease-in-out;
      }
      div[data-testid="stButton"] > button:hover {
        background-color: #f0fdf4 !important;
        transform: translateY(-2px);
      }
    </style>
    """, unsafe_allow_html=True)


params = st.query_params
student_id = params.get("student_id", [None])[0]

if student_id and "student_id" not in st.session_state:
    st.session_state["student_id"] = student_id

# Initialize DB
init_db()

# Load Razorpay config (only once)
RAZORPAY_CONFIG_PATH = "razorpay_config.json"
if os.path.exists(RAZORPAY_CONFIG_PATH):
    with open(RAZORPAY_CONFIG_PATH) as f:
        razorpay_config = json.load(f)
    razorpay_client = razorpay.Client(auth=(razorpay_config["key_id"], razorpay_config["key_secret"]))
else:
    razorpay_client = None


# =========================
# 2️⃣ Password Hashing & Check
# =========================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(login_input: str, password: str, role: str):
    from db import get_connection
    conn = get_connection()
    cur = conn.cursor()

    if role == "Student":
        cur.execute("""
            SELECT * FROM users 
            WHERE student_id=? AND password=? AND role=?
        """, (login_input, hash_password(password), role))
    else:
        cur.execute("""
            SELECT * FROM users 
            WHERE email=? AND password=? AND role=?
        """, (login_input, hash_password(password), role))

    user = cur.fetchone()
    conn.close()

    if not user:
        return None

    return {
        "id": user[0],
        "student_id": user[3],
        "student_name": user[4],
        "email": user[6],
        "role": user[8],
        "class": user[9],
        "section": user[10],
    }


# =========================
# 3️⃣ Login Page
# =========================
def render_login():
    import base64
    import streamlit as st

    # Load DPS banner
    banner_b64 = ""
    try:
        with open("dps_banner.png", "rb") as f:
            banner_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        pass

    # CSS
    st.markdown(f"""
    <style>
    /* Background */
    html, body, [data-testid="stAppViewContainer"], .main, .block-container {{
        background: #165B33 !important;
    }}
    header, footer {{display: none !important;}}

    /* Banner */
    .login-header img {{
        width: 100%;
        max-width: 600px;
        height: auto;
        display: block;
        margin: 1rem auto;
    }}

    /* Login form container (no ghost box!) */
    .stForm {{
        background: #fff;
        padding: 1.2rem;
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        width: 100%;
        max-width: 320px;
        margin: 0 auto; /* Center */
    }}

    /* Force visible labels */
    label, .stTextInput label, .stPasswordInput label, .stSelectbox label {{
        color: #000 !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }}

    /* Slimmer input fields */
    input, select, textarea {{
        height: 1.6rem !important;   /* ⬅️ reduced */
        font-size: 0.85rem !important;
        border-radius: 5px !important;
        padding: 0 0.4rem !important;
    }}

    /* Slimmer button */
    button[kind="secondary"] {{
        width: 100%;
        height: 1.9rem !important;   /* ⬅️ reduced */
        border-radius: 5px;
        font-weight: 600;
        font-size: 0.85rem !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Banner
    if banner_b64:
        st.markdown(f"<div class='login-header'><img src='data:image/png;base64,{banner_b64}'/></div>", unsafe_allow_html=True)
    else:
        st.markdown("<h2 style='color:white;text-align:center;'>DPS Narasaraopet</h2>", unsafe_allow_html=True)

    # Login Form (direct, no extra wrapper divs)
    with st.form("login_form_modern", clear_on_submit=False):
        login_input = st.text_input("Login ID (Email / Student ID)")
        password = st.text_input("Password", type="password")
        role_choice = st.selectbox("Role", ["HR", "Teacher", "Student", "Principal", "Front Office Admin", "Chairman", "Cafeteria", "Maintancence Incharge", "Bus Incharge", "Coordinator", "Finance Accountant", "Administrative officer", "Hostel warden"])
        login_btn = st.form_submit_button("Log In")

    if login_btn:
        user = check_password(login_input.strip(), password.strip(), role_choice)
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("❌ Invalid credentials")








# =========================
# 4️⃣ Role-based Dashboards
# =========================
if "user" not in st.session_state:
    render_login()
else:
    role = st.session_state["user"]["role"]
    user = st.session_state["user"]

    if role == "Admin":
        from modules.admin_dashboard import render_admin_dashboard
        render_admin_dashboard()

    elif role == "Teacher":
        from modules.teacher_dashboard import render_teacher_dashboard
        render_teacher_dashboard(user)

    elif role == "Student":
        apply_student_theme()  # ✅ make the green bg persistent after login
        
        # ✅ Start the GPS receiver (no-op if already started)
        start_gps_server_once()
        
        # ✅ FIX: import GROUPS and render_sub_item, and pass GROUPS to the dashboard
        from modules.student_dashboard import render_student_dashboard, render_sub_item, GROUPS
        render_student_dashboard(GROUPS)

        # If a tile/button was clicked, render that section using the user info
        if "item" in st.session_state and st.session_state["item"]:
            render_sub_item(st.session_state["item"], user)

        st.markdown("---")
        st.subheader("💳 Pay Your Fees")

        if not razorpay_client:
            st.warning("Razorpay config missing.")
        else:
            import streamlit.components.v1 as components

            if st.button("💵 Pay Now"):
                amount_rupees = 500
                amount_paise = amount_rupees * 100

                order = razorpay_client.order.create({
                    "amount": amount_paise,
                    "currency": "INR",
                    "payment_capture": 1
                })

                components.html(f"""
                <script src='https://checkout.razorpay.com/v1/checkout.js'></script>
                <script>
                    var options = {{
                        "key": "{razorpay_config['key_id']}",
                        "amount": "{order['amount']}",
                        "currency": "INR",
                        "name": "School",
                        "description": "Fees Payment",
                        "order_id": "{order['id']}",
                        "handler": function (response) {{
                            window.parent.postMessage({{
                                payment_id: response.razorpay_payment_id,
                                order_id: response.razorpay_order_id,
                                signature: response.razorpay_signature
                            }}, "*");
                        }},
                        "prefill": {{
                            "name": "{user['student_name']}",
                            "email": "student@example.com"
                        }},
                        "theme": {{
                            "color": "#3399cc"
                        }}
                    }};
                    var rzp = new Razorpay(options);
                    rzp.open();
                </script>
                """, height=500)

            if all(k in params for k in ["razorpay_payment_id", "razorpay_order_id", "razorpay_signature"]):
                st.success("✅ Payment Received!")
                try:
                    razorpay_client.utility.verify_payment_signature({
                        "razorpay_order_id": params["razorpay_order_id"][0],
                        "razorpay_payment_id": params["razorpay_payment_id"][0],
                        "razorpay_signature": params["razorpay_signature"][0]
                    })
                    st.success("🛡️ Signature verified!")
                except:
                    st.error("❌ Signature verification failed!")

    elif role == "Principal":
        from modules.principal_dashboard import render_principal_dashboard
        render_principal_dashboard(user)

    elif role == "Front Office Admin":
        from modules.frontoffice_dashboard import render_frontoffice_dashboard
        render_frontoffice_dashboard(user)
        
    elif role == "Chairman":
        from modules.chairman_dashboard import render_chairman_dashboard
        render_chairman_dashboard(user)


    # =========================
    # 5️⃣ Logout
    # =========================
    # st.sidebar.markdown("---")
    # if st.sidebar.button("🚪 Logout"):
        # st.session_state.clear()
        # st.rerun()
