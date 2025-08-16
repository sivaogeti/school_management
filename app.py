import streamlit as st
from db import init_db
import hashlib
import json
import razorpay
import os

# =========================
# 1️⃣ App Config
# =========================
st.set_page_config(page_title="🏫 School Management System", layout="wide")

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
    
    # Students authenticate via student_id
    if role == "Student":
        cur.execute("""
            SELECT * FROM users 
            WHERE student_id=? AND password=? AND role=?
        """, (login_input, hash_password(password), role))
    
    # All other roles authenticate via email
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
# 3️⃣ Login Flow
# =========================
if "user" not in st.session_state:
    st.title("🏫 School Management System")
    st.info("Please login to continue.")

    with st.form("login_form"):
        login_input = st.text_input("Email (for Staff) OR Student ID")
        password = st.text_input("Password", type="password")
        # 👇 Added "Admin" to role choices
        role_choice = st.selectbox("Role", ["Admin", "Teacher", "Student", "Principal", "Front Office Admin"])
        login_btn = st.form_submit_button("Login")

    if login_btn:
        user = check_password(login_input.strip(), password.strip(), role_choice)
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

else:
    # =========================
    # 4️⃣ Render Dashboards
    # =========================
    role = st.session_state["user"]["role"]
    user = st.session_state["user"]

    if role == "Admin":
        from modules.admin_dashboard import render_admin_dashboard
        render_admin_dashboard()

    elif role == "Teacher":
        from modules.teacher_dashboard import render_teacher_dashboard
        render_teacher_dashboard(user)

    elif role == "Student":
        from modules.student_dashboard import render_student_dashboard
        render_student_dashboard(user)

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

    # =========================
    # 5️⃣ Logout Option
    # =========================
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()
