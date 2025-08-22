# modules/student_dashboard.py
import os, re, base64, hashlib, requests
from datetime import datetime
import streamlit as st


def _ensure_green_bg():
    """Sticky light-green background, no overlays."""
    if st.session_state.get("_bg_css_done"):
        return
    st.markdown("""
    <style>
      :root { --app-bg: #e8f5e9; }

      /* Global background */
      html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        background: var(--app-bg) !important;
      }
      /* Keep blocks transparent so background shows through */
      .main, .block-container,
      [data-testid="stVerticalBlock"], [data-testid="stVerticalBlock"] > div,
      [data-testid="stHorizontalBlock"], [data-testid="stHorizontalBlock"] > div {
        background: transparent !important;
      }

      /* Tile buttons: scoped to #tiles only so Logout isn't affected */
      #tiles div[data-testid="stButton"] > button {
        background-color: #ffffff !important;
        border: 1px solid #ddd !important;
        border-radius: 12px !important;
        padding: 1.0rem 1rem !important;
        margin: 0.5rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.08);
        transition: transform .15s ease;
      }
      #tiles div[data-testid="stButton"] > button:hover {
        transform: translateY(-2px);
      }

      /* Compact logout only */
      #logout-area button {
        padding: 0.35rem 0.8rem !important;
        font-size: 0.95rem !important;
        line-height: 1.1rem !important;
        border-radius: 10px !important;
        margin: 0 !important;
        width: auto !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.12) !important;
      }

      /* Logo sizing */
      #top-logo img {
        max-width: 820px;
        width: 100%;
        display: block;
        margin: 0 auto;
      }
    </style>
    """, unsafe_allow_html=True)
    st.session_state["_bg_css_done"] = True


def _student_topbar():
    """Top bar with Welcome (left), bigger logo (center), compact Logout (right),
    and a single back button decided here only."""
    _ensure_green_bg()
    
    # Scoped CSS for logo + compact logout (overrides any tile styles)
    st.markdown("""
    <style>
      /* Bigger centered logo */
      #top-logo img {
        max-width: 900px;   /* increase/decrease to taste */
        width: 100%;
        height: auto;
        display: block;
        margin: 0 auto;
      }

      /* Compact logout button only in this area */
      #logout-area div[data-testid="stButton"] > button {
        padding: 0.35rem 0.9rem !important;
        margin: 0 !important;
        width: auto !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,.12) !important;
      }
    </style>
    """, unsafe_allow_html=True)

    user = st.session_state.get("user", {}) or {}
    name = user.get("student_name") or user.get("student_id") or "Student"

    # Decide which back to show
    show_back_to_groups   = bool(st.session_state.get("group")) and not st.session_state.get("item")
    show_back_to_sections = bool(st.session_state.get("item"))

    c1, c2, c3 = st.columns([1.0, 3.0, 1.0])
    with c1:
        st.markdown(f"### Welcome, {name}")
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        
        # Top-left back button (only here)
        if show_back_to_sections:
            if st.button("⬅ Back to sections", key="back-from-item-top"):
                st.session_state["item"] = None
                st.rerun()
        elif show_back_to_groups:
            if st.button("⬅ Back to groups", key="back-to-groups-top"):
                st.session_state["group"] = None
                st.session_state["item"] = None
                st.rerun()

    with c2:
        logo_bytes = _load_logo_bytes() 
        #if "_load_logo_bytes" in globals() else None
        if logo_bytes:
            st.markdown("<div id='top-logo'>", unsafe_allow_html=True)
            st.image(logo_bytes, use_container_width=True)  # responsive, large
            st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("<div id='logout-area' style='text-align:right;'>", unsafe_allow_html=True)
        if st.button("🚪 Logout", key="student_logout"):
            st.session_state.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='opacity:.25' />", unsafe_allow_html=True)

import pandas as pd
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI
from db import get_connection
from modules.help_widget import render_help_widget
from modules.curated_videos import CURATED_VIDEOS
#import streamlit_camera_input_live.camera_input_live as cam
import uuid
import altair as alt 

client = OpenAI(api_key=st.secrets["api_keys"]["openai_api_key"])
st.write("DEBUG OpenAI Key starts with:", st.secrets["api_keys"]["openai_api_key"][:6])



if "ai_tutor_history" not in st.session_state:
    st.session_state.ai_tutor_history = []

#This is for 📚 Chapter-wise Learning insight
def parse_quiz(quiz_text: str):
    """
    Parse GPT quiz text into structured questions & answers.
    Handles:
    Q1: ...
    1. ...
    A) ...
    - A) ...
    Option A: ...
    A. ...
    Correct: A) ...
    """
    questions = []
    current_q = None

    for line in quiz_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Match Question (Q1, Q2, 1., etc.)
        if re.match(r"^(q?\d+[:.)])", line, re.IGNORECASE):
            current_q = {"q": line, "options": [], "correct": None}
            questions.append(current_q)

        # Match Options
        elif re.match(r"^(-?\s*option\s*[ABCD]|[-\s]*[ABCD])[).:]", line, re.IGNORECASE):
            if current_q:
                clean = re.sub(
                    r"^(-?\s*option\s*|[-\s]*)([ABCD])[).:]\s*",
                    r"\2) ",
                    line,
                    flags=re.IGNORECASE
                )
                current_q["options"].append(clean)

        # Match Correct Answer
        elif "correct" in line.lower() and current_q:
            ans = line.split(":")[-1].strip()
            current_q["correct"] = ans

    return questions

#this is for 📚 Chapter-wise Learning insight
@st.cache_data(show_spinner=False)
def get_quiz(subject, chapter):
    q_prompt = f"""
    Generate 3 multiple-choice questions with 4 options each for '{chapter}' in {subject}.
    Use this exact format:
    Q1: <question text>
    A) <option>
    B) <option>
    C) <option>
    D) <option>
    Correct: <letter>
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a quiz generator for school students. Always return in strict MCQ format."},
            {"role": "user", "content": q_prompt}
        ]
    )
    return completion.choices[0].message.content

# --- Curated videos lookup ---
def get_curated_video(query: str):
    q = query.lower().strip()
    for keyword, url in CURATED_VIDEOS.items():
        if keyword in q:
            return url
    return None

# Folder to store diagrams locally-> this is for 📚 Chapter-wise Learning insight
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DIAGRAM_DIR = os.path.join(BASE_DIR, "data", "diagrams")
os.makedirs(DIAGRAM_DIR, exist_ok=True)

# this is for 📚 Chapter-wise Learning insight
def _safe_filename(text: str) -> str:
    """Generate a safe, unique filename based on text."""
    return hashlib.md5(text.encode()).hexdigest() + ".png"
    
#This is for Transport
# --- ONE-TIME helper: make sure route table has in-charge columns ---
def _ensure_transport_schema(conn):
    """SQLite-safe: add columns if they don't exist, no-op otherwise."""
    cur = conn.cursor()

    # Check existing columns
    cur.execute("PRAGMA table_info(transport_routes)")
    cols = {row[1] for row in cur.fetchall()}

    # Add missing columns (ignore errors if they already exist)
    if "incharge_name" not in cols:
        try:
            cur.execute("ALTER TABLE transport_routes ADD COLUMN incharge_name TEXT")
        except Exception:
            pass
    if "incharge_phone" not in cols:
        try:
            cur.execute("ALTER TABLE transport_routes ADD COLUMN incharge_phone TEXT")
        except Exception:
            pass

    conn.commit()

    
#This is for 💰 My Fees & Payments
def render_fee_management(sid, available_years):
    """
    Fee Management Table with:
      ✅ Academic year dropdown
      ✅ Grouped headers (Fee Due / Fee Paid under each category)
      ✅ Balance per month
      ✅ Grand Total row
      ✅ Missing months handled (April→March)
      ✅ Row shading if unpaid/cleared
      ✅ Summary metrics at top
    """
    import pandas as pd
    import streamlit as st
    from db import get_connection

    _render_card("💰 My Fees & Payments")

    try:
        # --- Academic Year Dropdown ---
        academic_year = st.selectbox("Select Academic Year", available_years, index=len(available_years)-1)

        # --- Month mapping (Apr→Mar) ---
        months_order = ["04","05","06","07","08","09","10","11","12","01","02","03"]
        months_map   = {
            "04": "April", "05": "May", "06": "June", "07": "July",
            "08": "August", "09": "September", "10": "October", "11": "November",
            "12": "December", "01": "January", "02": "February", "03": "March"
        }

        conn = get_connection()
        cur = conn.cursor()

        # --- Dues ---
        cur.execute("""
            SELECT month,
                   tuition_due, bus_due, food_due, books_due,
                   uniform_due, hostel_due, misc_due
            FROM fee_schedule
            WHERE student_id = ? AND academic_year = ?
        """, (sid, academic_year))
        dues = pd.DataFrame(cur.fetchall(), columns=[
            "month","tuition_due","bus_due","food_due","books_due",
            "uniform_due","hostel_due","misc_due"
        ])

        # --- Payments ---
        cur.execute("""
            SELECT strftime('%m', date) as month,
                   SUM(amount) as paid
            FROM payments
            WHERE student_id=?
            GROUP BY strftime('%m', date)
        """, (sid,))
        payments = pd.DataFrame(cur.fetchall(), columns=["month","paid"])
        conn.close()

        # --- Ensure all months exist ---
        all_months = pd.DataFrame({"month": months_order})
        dues = all_months.merge(dues, on="month", how="left").fillna(0)
        payments = all_months.merge(payments, on="month", how="left").fillna(0)

        # --- Merge dues + payments ---
        df = dues.merge(payments, on="month", how="left").fillna(0)
        df["month_name"] = df["month"].map(months_map)

        # --- For each category, compute Fee Paid (simple proportional split not shown, just lump sum against tuition) ---
        categories = ["tuition","bus","food","books","uniform","hostel","misc"]

        # Split "paid" column into these categories? 
        # For now, assume "paid" applies to tuition (simple demo).
        for c in categories:
            df[f"{c}_paid"] = 0
        df["tuition_paid"] = df["paid"]

        # --- Balance ---
        df["balance"] = (
            df["tuition_due"] + df["bus_due"] + df["food_due"] +
            df["books_due"] + df["uniform_due"] + df["hostel_due"] + df["misc_due"]
            - df["paid"]
        )

        # --- Build MultiIndex columns ---
        arrays = []
        for c in categories:
            title = {
                "tuition":"Tuition Fee","bus":"Bus Fee","food":"Food Fee",
                "books":"Book Fee","uniform":"Uniform Fee",
                "hostel":"Hostel Fee","misc":"Miscellaneous"
            }[c]
            arrays.append((title,"Fee Due"))
            arrays.append((title,"Fee Paid"))
        arrays.append(("Balance","Balance"))

        columns = pd.MultiIndex.from_tuples(arrays)

        # --- Build display DataFrame ---
        records = []
        for _, row in df.iterrows():
            rec = []
            for c in categories:
                rec.append(int(row[f"{c}_due"]))
                rec.append(int(row[f"{c}_paid"]))
            rec.append(int(row["balance"]))
            records.append(rec)

        display_df = pd.DataFrame(records, columns=columns, index=df["month_name"])

        # --- Grand Total ---
        totals = []
        for c in categories:
            totals.append(int(df[f"{c}_due"].sum()))
            totals.append(int(df[f"{c}_paid"].sum()))
        totals.append(int(df["balance"].sum()))
        display_df.loc["Grand Total"] = totals

        # --- Summary cards ---
        total_due = sum(df[f"{c}_due"].sum() for c in categories)
        total_paid = sum(df[f"{c}_paid"].sum() for c in categories)
        total_bal  = int(df["balance"].sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Fee", f"₹{total_due}")
        c2.metric("Total Paid", f"₹{total_paid}")
        c3.metric("Balance", f"₹{total_bal}")

        # --- Style ---
        def style_table(df):
            styles = pd.DataFrame("", index=df.index, columns=df.columns)

            # highlight balance
            styles.loc[df[("Balance","Balance")] > 0, ("Balance","Balance")] = "color:red; font-weight:bold;"
            styles.loc[df[("Balance","Balance")] <= 0, ("Balance","Balance")] = "color:green; font-weight:bold;"

            # row shading
            for i in df.index:
                if i != "Grand Total":
                    if df.loc[i, ("Balance","Balance")] > 0:
                        styles.loc[i,:] = "background-color:#ffe5e5;"
                    else:
                        styles.loc[i,:] = "background-color:#e5ffe5;"
            return styles

        styled = (display_df.style
                  .set_table_styles([{
                      "selector": "th",
                      "props": [("font-weight", "bold"), ("background-color", "#f0f0f0")]
                  }])
                  .apply(style_table, axis=None))

        st.dataframe(styled, use_container_width=True)

    except Exception as e:
        st.error(f"Error fetching fee data: {e}")

#this is for ai_tutor_response
# --- Preloaded diagrams (always use if available) ---
PRELOADED_DIAGRAMS = {
    "point": os.path.join(DIAGRAM_DIR, "point.png"),
    "line": os.path.join(DIAGRAM_DIR, "line.png"),
    "circle": os.path.join(DIAGRAM_DIR, "circle.png"),
    "triangle": os.path.join(DIAGRAM_DIR, "triangle.png"),
    "square": os.path.join(DIAGRAM_DIR, "square.png"),
    "rectangle": os.path.join(DIAGRAM_DIR, "rectangle.png"),
    "cube": os.path.join(DIAGRAM_DIR, "cube.png"),
    "sphere": os.path.join(DIAGRAM_DIR, "sphere.png"),
    "cone": os.path.join(DIAGRAM_DIR, "cone.png"),
    "cylinder": os.path.join(DIAGRAM_DIR, "cylinder.png"),
    "pyramid": os.path.join(DIAGRAM_DIR, "pyramid.png"),
}



# --- AI Tutor core function ---
@st.cache_data(show_spinner=False)
def ai_tutor_response(user_input: str):
    """
    AI Tutor: returns explanation + optional diagram (local path).
    Priority:
      1. Preloaded diagrams (point.png, cube.png, etc.)
      2. Cached in DB/disk
      3. Generate with OpenAI → save locally → DB
    """
    try:
        # --- Generate text explanation ---
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI Tutor for school students."},
                {"role": "user", "content": user_input}
            ]
        )
        response_text = completion.choices[0].message.content

        # --- Diagram handling ---
        image_path = None
        query_lower = user_input.lower()

        # 1️⃣ Preloaded diagrams
        for keyword, path in PRELOADED_DIAGRAMS.items():
            if keyword in query_lower and os.path.exists(path):
                image_path = path
                return response_text, image_path

        # 2️⃣ DB/disk cached diagrams
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS diagrams (
                concept TEXT PRIMARY KEY,
                file_path TEXT
            )
        """)
        cur.execute("SELECT file_path FROM diagrams WHERE concept=?", (query_lower,))
        row = cur.fetchone()

        if row and os.path.exists(row[0]):
            image_path = row[0]
            conn.close()
            return response_text, image_path

        # 3️⃣ Generate with OpenAI and save
        try:
            image = client.images.generate(
                model="gpt-image-1",
                prompt=f"Educational diagram of {user_input}",
                size="512x512"
            )
            image_url = image.data[0].url

            # Save locally
            fname = _safe_filename(user_input)
            local_path = os.path.join(DIAGRAM_DIR, fname)
            r = requests.get(image_url)
            if r.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(r.content)
                image_path = local_path
                # Save path in DB
                cur.execute("INSERT OR REPLACE INTO diagrams (concept, file_path) VALUES (?, ?)", 
                            (query_lower, local_path))
                conn.commit()
        except Exception:
            image_path = None

        conn.close()
        return response_text, image_path

    except Exception as e:
        return f"AI Tutor Error: {str(e)}", None



YOUTUBE_API_KEY = "AIzaSyAQw29Zt3bIiGzCsvekq-brJFZdctFpfQM"  # put in .env or OS environment

def get_video_url(query: str) -> str:
    """Return safe educational video URL for the query."""
    q = query.lower().strip()

    # Step 1: Check curated safe list first
    for keyword, url in CURATED_VIDEOS.items():
        if keyword in q:
            return url

    # Step 2: Fallback → YouTube API Search
    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query + " Khan Academy OR CrashCourse OR educational",
        "type": "video",
        "maxResults": 1,
        "key": "AIzaSyAQw29Zt3bIiGzCsvekq-brJFZdctFpfQM"
    }
    try:
        r = requests.get(search_url, params=params)
        r.raise_for_status()
        items = r.json().get("items", [])
        if items:
            video_id = items[0]["id"]["videoId"]
            return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        print("YouTube API error:", e)

    return None  # if no results


#render_receipts function for receipts
def render_receipts(user):
    import pandas as pd
    import streamlit as st
    from db import get_connection

    st.subheader("📜 Receipts")

    try:
        conn = get_connection()
        query = """
            SELECT 
                receipt_no AS "Rec No.",
                payment_item AS "Type",
                date AS "Date",
                amount AS "Amount",
                mode AS "Mode",
                late_fine AS "Late Fine",
                transaction_id AS "Transaction ID"
            FROM receipts
            WHERE student_id = ?
            ORDER BY date DESC
        """
        df = pd.read_sql(query, conn, params=(user["student_id"],))
        conn.close()

        if not df.empty:
            # --- Format columns ---
            df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%d-%m-%y")
            df["Amount"] = df["Amount"].apply(lambda x: f"Rs.{x:,.0f}")
            df["Late Fine"] = df["Late Fine"].apply(lambda x: f"Rs.{x:,.0f}")

            # --- Totals ---
            total_receipts = len(df)
            cancelled = df[df["Mode"].str.upper() == "CANCELLED"].shape[0]
            live = total_receipts - cancelled

            st.markdown(
                f"**Total Receipt : {total_receipts} "
                f"<span style='color:red'>Cancelled : {cancelled}</span> "
                f"<span style='color:green'>Live : {live}</span>**",
                unsafe_allow_html=True
            )

            # --- Highlight cancelled rows ---
            def highlight_cancelled(row):
                if str(row["Mode"]).upper() == "CANCELLED":
                    return ["background-color: #ffcccc; text-decoration: line-through;"] * len(row)
                else:
                    return [""] * len(row)

            styled_df = df.style.apply(highlight_cancelled, axis=1)

            # --- Show styled dataframe ---
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

        else:
            st.info("No receipts available yet.")

    except Exception as e:
        st.error(f"Error loading receipts: {e}")


# 🔹 Common UI helper functions
def render_card(title: str):
    """Renders a section header with consistent style."""
    st.markdown(f"### {title}")
    st.write("---")

def end_card():
    """Adds spacing after a section to keep UI clean."""
    st.write("")
    st.write("")

#Marks
def render_my_marks(student_id: int) -> None:
    import altair as alt  # safe to import here if not at module top

    # --- Fetch Data from DB ---
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT exam_date as Date,
               subject as Subject,
               exam_type as "Exam Type",
               total_marks AS "Max Marks",
               secured_marks AS "Secured Marks"
        FROM marks
        WHERE fk_student_id = ?
        ORDER BY exam_date
    """, (student_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        st.warning("No marks data available for this student.")
        return

    # --- Build DataFrame with expected columns ---
    df = pd.DataFrame(rows, columns=["Date", "Subject", "Exam Type", "Max Marks", "Secured Marks"])

    # Ensure correct dtypes
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Max Marks"] = pd.to_numeric(df["Max Marks"], errors="coerce").fillna(0)
    df["Secured Marks"] = pd.to_numeric(df["Secured Marks"], errors="coerce").fillna(0)

    # --- Percentage column (rounded for display) ---
    df["Percentage"] = ((df["Secured Marks"] / df["Max Marks"]) * 100).round(1).fillna(0)

    # --- Build exam type options (no None/nan) and include "All Exams" ---
    exam_options = df["Exam Type"].dropna().astype(str).unique().tolist()
    exam_options = ["All Exams"] + exam_options

    # Choose radio for small lists, selectbox for many
    if len(exam_options) <= 6:
        selected_exam = st.radio("Select Exam Type:", exam_options, index=0, horizontal=True)
    else:
        selected_exam = st.selectbox("Select Exam Type:", exam_options, index=0)

    # --- Filter dataframe ---
    if selected_exam == "All Exams":
        filtered_df = df.copy()
    else:
        filtered_df = df[df["Exam Type"].astype(str) == selected_exam].copy()

    # --- Show Marks Table FIRST (student-facing) ---
    st.subheader("📋 Marks Table")
    if filtered_df.empty:
        st.info(f"No records found for **{selected_exam}**.")
        return

    # Display Date as date-only for table
    display_df = filtered_df[["Date", "Subject", "Max Marks", "Secured Marks", "Percentage"]].copy()
    display_df["Date"] = display_df["Date"].dt.date

    # Show table
    st.dataframe(display_df, use_container_width=True)

    # --- Summary metric (Total Obtained / Percentage) ---
    total_secured = int(filtered_df["Secured Marks"].sum())
    total_max = int(filtered_df["Max Marks"].sum())
    overall_pct = round((total_secured / total_max) * 100, 1) if total_max > 0 else 0
    st.metric("Total Obtained", f"{total_secured} / {total_max}", f"{overall_pct}%")

    st.markdown("---")

    # --- Chart 1: Grouped Bar (Secured vs Max Marks per Subject) ---
    chart_df = filtered_df.copy()

    chart1 = (
        alt.Chart(chart_df)
        .transform_fold(["Secured Marks", "Max Marks"], as_=["Type", "Marks"])
        .mark_bar()
        .encode(
            x=alt.X(
                "Subject:N", 
                title="Subject",
                sort=alt.EncodingSortField(
                    field="Marks",              # sort by numeric field
                    op="sum",                   # aggregate operation (sum, mean, etc.) 
                    order="descending"          # descending order
                )
            ),                 
            xOffset=alt.XOffset("Type:N"),                         # <- side-by-side grouping
            y=alt.Y("Marks:Q", title="Marks"),
            color=alt.Color(
                "Type:N",
                title="Mark Type",
                scale=alt.Scale(
                    domain=["Max Marks", "Secured Marks"],         # keep legend/order stable
                    range=["#4C78A8", "#9C9C9C"]                   # new colors
                ),
            ),
            tooltip=[
                alt.Tooltip("Subject:N"),
                alt.Tooltip("Type:N"),
                alt.Tooltip("Marks:Q")
            ],
            order=alt.Order("Type:N")                              # consistent draw order
        )
        .properties(title=f"Secured vs Max Marks — {selected_exam}")
    )

    st.altair_chart(chart1, use_container_width=True)
    
    

    # --- Chart 2: Pie + Side Table ---
    subject_totals = (
        chart_df.groupby("Subject", as_index=False)
        .agg({"Secured Marks": "sum", "Max Marks": "sum"})
    )
    subject_totals["Percentage"] = ((subject_totals["Secured Marks"] / subject_totals["Max Marks"]) * 100).round(1).fillna(0)

    col1, col2 = st.columns([2, 1])
    with col1:
        pie = (
            alt.Chart(subject_totals)
            .mark_arc()
            .encode(
                theta=alt.Theta("Secured Marks:Q"),
                color=alt.Color("Subject:N", title="Subject"),
                tooltip=[
                    alt.Tooltip("Subject:N"),
                    alt.Tooltip("Secured Marks:Q"),
                    alt.Tooltip("Percentage:Q", format=".1f")
                ],
            )
            .properties(title="Subject-wise Contribution (Pie)")
        )
        st.altair_chart(pie, use_container_width=True)

    with col2:
        st.write("### Subject Summary")
        st.dataframe(subject_totals[["Subject", "Secured Marks", "Percentage"]], use_container_width=True, hide_index=True)

    # --- Chart 3: Trend (only if more than one exam date present) ---
    if filtered_df["Date"].nunique() > 1:
        # Trend of percentage over time (aggregated by date & subject)
        trend_df = filtered_df.sort_values("Date").copy()
        trend = (
            alt.Chart(trend_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("Date:T", title="Exam Date"),
                y=alt.Y("Percentage:Q", title="Percentage"),
                color=alt.Color("Subject:N", title="Subject"),
                tooltip=[alt.Tooltip("Date:T"), alt.Tooltip("Subject:N"), alt.Tooltip("Percentage:Q", format=".1f")]
            )
            .properties(title="Performance Trend Over Time")
        )
        st.altair_chart(trend, use_container_width=True)
    else:
        st.info("Trend chart not applicable for a single exam/date selection.")

    

    
    

# ---------- Paths ----------
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")

# ---------- Default lesson plans ----------
LESSON_PLANS = {
    "Mathematics": [
        {"chapter": "Algebra", "notes": "Intro to equations"},
        {"chapter": "Geometry", "notes": "Triangles basics"}
    ],
    "Science": [
        {"chapter": "Physics - Motion", "notes": "Laws of motion summary"}
    ]
}

# ---------- Groups / items / colors ----------
GROUPS = {
    "📘 Academics & Learning": {
        "color": "#2563eb",
        "items": [
            ("📚 Chapter-wise Learning Insight", "#2563eb"),            
            ("🤖 AI Tutor (24/7)", "#9333ea"),
        ],
    },
    "📊 Student Progress": {
        "color": "#16a34a",
        "items": [
            ("📊 My Marks", "#16a34a"),
            ("✅ My Attendance", "#22c55e"),
            ("📈 Performance Insights", "#0284c7"),
            ("📤 Submit Assignments (AI Checked)", "#d97706"),
            ("🗂️ Homework", "#7c3aed"),
        ],
    },
    "💰 Fee Management": {
        "color": "#ea580c",
        "items": [
            ("💰 My Fees & Payments", "#ea580c"),
            ("📜 Receipts", "#f97316"),
            ("💳 Pay Online", "#f59e0b"),
        ],
    },
    "🍴🏠 Cafeteria & Hostel": {
        "color": "#7c3aed",
        "items": [
            ("🥗 Daily Menu", "#16a34a"),
            ("🛏️ Hostel Info", "#7c3aed"),
        ],
    },
    "🚌 Transport & Safety": {
        "color": "#dc2626",
        "items": [
            ("🚌 Transport Info", "#dc2626"),            
            ("📍 Live Bus Tracking", "#f59e0b"),
        ],
    },
    "📢 Communication & Engagement": {
        "color": "#0891b2",
        "items": [
            ("📰 School Notices", "#0891b2"),
            ("📢 Message History", "#9333ea"),
            ("📨 Messages", "#16a34a"),
        ],
    },
    "📑 Encyclopedia": {
        "color": "#4f46e5",
        "items": [
            ("🖼️ Gallery", "#16a34a"),
            ("📅 Timetable", "#2563eb"),
            ("🎉 Special Days", "#f59e0b"),
            ("📊 Academic Assessment Calendar", "#9333ea"),
            ("🏆 Competitions & Enrichment Programs", "#dc2626"),
            ("📘 Key Guidelines", "#0ea5e9"),
            ("💬 Complaints & Suggestions", "#6b7280"),
        ],
    }
}


# ---------- Helpers ----------
def _safe_id(text: str) -> str:
    return "id_" + "".join(c for c in text if c.isalnum()).lower()

def _inject_button_css(scope_id: str, color: str):
    st.markdown(f"""
    <style>
    div#{scope_id} div[data-testid="stButton"] > button {{
        width: 100%;
        background: {color} !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 10px 14px !important;
        margin: 6px 0 12px 0 !important;
        transition: filter .15s ease, transform .02s ease;
        box-shadow: 0 2px 6px rgba(0,0,0,.12);
    }}
    div#{scope_id} div[data-testid="stButton"] > button:hover {{
        filter: brightness(92%);
    }}
    div#{scope_id} div[data-testid="stButton"] > button:active {{
        transform: translateY(1px);
    }}
    </style>
    """, unsafe_allow_html=True)

def _inject_base_css():
    st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .main, .block-container {
        background: #e6f4ea !important;
    }
    .card {
        border-radius: 12px;
        padding: 0.75rem 1rem;
        margin: 10px 0 14px 0;
        text-align: left;
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,.06);
    }
    .card-title { font-weight: 700; font-size: 1.05rem; margin-bottom: .35rem; }
    .card-subtle { color: #6b7280; font-size: .9rem; }
    .dashboard-welcome { font-weight: 700; color: #165B33; }
    </style>
    """, unsafe_allow_html=True)

def _render_card(title: str, subtitle: str = ""):
    st.markdown(f"<div class='card'><div class='card-title'>{title}</div><div class='card-subtle'>{subtitle}</div>", unsafe_allow_html=True)

def _end_card():
    st.markdown("</div>", unsafe_allow_html=True)

def _load_logo_bytes():
    paths = [os.path.join(BASE_DIR, "dps_banner.png"), os.path.join(BASE_DIR, "static", "dps_banner.png"),
             "dps_banner.png", "static/dps_banner.png"]
    for p in paths:
        try:
            if os.path.exists(p):
                with open(p, "rb") as f:
                    return f.read()
        except:
            pass
    return None

def _chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

# ---------- Sub-item Rendering ----------
def render_sub_item(item: str, user: dict):
    _student_topbar()
    sid = user.get("student_id")
    email = user.get("email")
    conn = get_connection()
    cur = conn.cursor()

    # --- My Marks ---
    if item == "📊 My Marks":
        render_my_marks(user["id"])

    # --- My Attendance ---
    elif item == "✅ My Attendance":
        import altair as _alt  # safe alias

        _render_card("✅ My Attendance")
        try:
            cur.execute(
                "SELECT date, status FROM attendance WHERE student_id=? ORDER BY date ASC",
                (sid,)
            )
            rows = cur.fetchall()
            #st.write(rows)
            #st.write("DEBUG student_id used:", sid)
            if rows:
                df = pd.DataFrame(rows, columns=["Date", "Status"])
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.dropna(subset=["Date"])

                # --- Build month keys from the FULL df (no pre-filter) ---
                # Keys like "2025-01", labels like "January 2025"
                month_keys = (
                    df["Date"]
                    .dt.to_period("M")
                    .sort_values()
                    .astype(str)
                    .unique()
                    .tolist()
                )
                month_labels = (
                    pd.to_datetime(month_keys, format="%Y-%m")
                    .strftime("%B %Y")
                    .tolist()
                )

                # Safety: if something odd, bail gracefully
                if not month_keys:
                    st.info("No valid dates available in attendance.")
                    _end_card()
                    return

                # --- Month picker with a UNIQUE key to avoid widget collisions ---
                choice_idx = st.selectbox(
                    "📅 Select Month",
                    options=list(range(len(month_keys))),
                    format_func=lambda i: month_labels[i],
                    index=len(month_keys) - 1,                  # latest month by default
                    key=f"att_month_{sid}"                      # <- unique per student
                )
                selected_month_key = month_keys[choice_idx]     # e.g., "2025-06"
                selected_month_label = month_labels[choice_idx] # e.g., "June 2025"

                # --- Filter by chosen month key ---
                filtered_df = df[df["Date"].dt.to_period("M").astype(str) == selected_month_key]

                # Show raw data
                st.dataframe(filtered_df, use_container_width=True)

                # --- Aggregate status counts ---
                counts = filtered_df["Status"].value_counts().reset_index()
                counts.columns = ["Status", "Count"]

                # Ensure fixed order & missing categories
                all_statuses = ["Present", "Absent", "Leave", "Late"]
                for status in all_statuses:
                    if status not in counts["Status"].values:
                        counts.loc[len(counts)] = [status, 0]
                counts["Status"] = pd.Categorical(counts["Status"], categories=all_statuses, ordered=True)
                counts = counts.sort_values("Status").reset_index(drop=True)

                total = counts["Count"].sum()
                counts["Share"] = counts["Count"] / total if total > 0 else 0

                # --- Donut Chart (Altair) ---
                chart = (
                    _alt.Chart(counts)
                    .mark_arc(innerRadius=50)
                    .encode(
                        theta=_alt.Theta("Share:Q", stack=True),
                        color=_alt.Color(
                            "Status:N",
                            title="Attendance Status",
                            scale=_alt.Scale(
                                domain=all_statuses,
                                range=["#4CAF50", "#E53935", "#FFB300", "#2196F3"]  # Late = blue
                            ),
                            legend=_alt.Legend(orient="right")
                        ),
                        tooltip=[
                            _alt.Tooltip("Status:N"),
                            _alt.Tooltip("Count:Q"),
                            _alt.Tooltip("Share:Q", format=".0%")
                        ]
                    )
                    .properties(
                        title=f"Attendance Summary — {selected_month_label}",
                        width=400, height=400
                    )
                )

                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.altair_chart(chart, use_container_width=True)

            else:
                st.info("No attendance records found.")

        except Exception as e:
            st.error(f"Error fetching attendance: {e}")

        _end_card()




    # --- School Notices ---
    elif item == "📰 School Notices":
        _render_card("📰 School Notices")
        today = datetime.today().strftime("%Y-%m-%d")
        try:
            cur.execute("SELECT title,message,created_by,timestamp FROM notices WHERE expiry_date IS NULL OR expiry_date>=? ORDER BY timestamp DESC", (today,))
            rows = cur.fetchall()
            if rows:
                for title,msg,creator,ts in rows:
                    with st.expander(f"{title} — {ts}"):
                        st.write(msg)
                        st.caption(f"Posted by {creator}")
            else:
                st.info("No active notices.")
        except:
            st.error("Error fetching notices.")
        _end_card()

    # --- 📚 Chapter-wise Learning insight ---
    elif item == "📚 Chapter-wise Learning Insight":
        _render_card("📚 Chapter-wise Learning Insight")

        # --- Subject Selection ---
        if "lesson_subject" not in st.session_state or st.session_state.lesson_subject not in LESSON_PLANS:
            st.session_state.lesson_subject = list(LESSON_PLANS.keys())[0]

        subject = st.selectbox(
            "Select Subject",
            list(LESSON_PLANS.keys()),
            index=list(LESSON_PLANS.keys()).index(st.session_state.lesson_subject)
        )
        st.session_state.lesson_subject = subject

        # --- DB Chapters / Fallback ---
        try:
            cur.execute(
                "SELECT chapter, notes FROM lesson_plans WHERE subject=? AND class=? AND section=?",
                (subject, user.get("class"), user.get("section"))
            )
            rows = cur.fetchall()
            chapters = [{"chapter": r[0], "notes": r[1]} for r in rows] if rows else LESSON_PLANS.get(subject, [])
        except:
            chapters = LESSON_PLANS.get(subject, [])

        # --- Cached AI Functions ---
        @st.cache_data(show_spinner=False)
        def get_explanation(subject, chapter):
            exp_prompt = f"Explain the chapter '{chapter}' in {subject} for school students, simple language, with diagram if useful."
            return ai_tutor_response(exp_prompt)

        if chapters:
            for ch in chapters:
                with st.expander(f"📖 {ch['chapter']}"):
                    # --- AI Explanation ---
                    explanation, image_path = get_explanation(subject, ch['chapter'])
                    st.markdown("### 📘 Explanation")
                    st.markdown(explanation)
                    if image_path:   # ✅ only display if available
                        st.image(image_path, caption="Illustration")

                    # --- Video ---
                    st.markdown("### 🎥 Related Video")
                    video_url = get_video_url(ch['chapter'])
                    if video_url:
                        st.video(video_url)

                    # --- Practice Questions ---
                    st.markdown("### 📝 Practice Questions")
                    quiz_text = get_quiz(subject, ch['chapter'])

                    # Parse quiz into structured Q&A
                    questions = parse_quiz(quiz_text)

                    
                    # Display MCQs with radio buttons
                    student_answers = {}
                    for i, q in enumerate(questions):
                        student_answers[q["q"]] = st.radio(
                            q["q"], q["options"], key=f"ans_{ch['chapter']}_{i}"
                        )

                    # Submit Button
                    if st.button(f"Submit Answers - {ch['chapter']}"):
                        score = 0
                        results = []
                        for q in questions:
                            correct = q.get("correct", "")
                            chosen = student_answers[q["q"]]
                            if chosen == correct:
                                st.success(f"✅ {q['q']} — Correct")
                                score += 1
                            else:
                                st.error(f"❌ {q['q']} — Your Answer: {chosen} | Correct: {correct}")
                            results.append((q["q"], correct, chosen, int(chosen == correct)))

                        st.info(f"Final Score: {score}/{len(questions)}")

                        # --- Save results in DB ---
                        conn = get_connection()
                        cur = conn.cursor()
                        for q, corr, stud, is_corr in results:
                            cur.execute("""
                                INSERT INTO chapter_practice 
                                (student_id, subject, chapter, question, correct_answer, student_answer, is_correct)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (user.get("id"), subject, ch['chapter'], q, corr, stud, is_corr))
                        conn.commit()
                        conn.close()
                        st.info("📊 Your answers have been saved for teacher review.")
        else:
            st.info("No insights available for this subject.")

        _end_card()


    # --- Homework---
    elif item == "🗂️ Homework":
        _render_card("📌 Homework")
        try:
            cur.execute(
                """
                SELECT subject, description, due_date, file_url, assigned_by, timestamp
                FROM homework
                WHERE class = ? AND section = ?
                ORDER BY timestamp DESC
                """,
                (user.get("class"), user.get("section"))
            )
            rows = cur.fetchall()

            if rows:
                for subj, desc, due, fname, assigned_by, ts in rows:
                    with st.expander(f"{subj} — Due: {due} — {ts}"):
                        if desc:
                            st.write(desc)
                        if assigned_by:
                            st.caption(f"Assigned by: {assigned_by}")

                        if fname:
                            path = os.path.join(UPLOAD_DIR, fname)
                            if os.path.exists(path):
                                with open(path, "rb") as f:
                                    st.download_button(
                                        "Download File",
                                        data=f.read(),
                                        file_name=fname
                                    )
                            else:
                                st.warning(f"File not found: {fname}")
            else:
                st.info("No homework posted.")
        except Exception as e:
            st.error(f"Error fetching homework: {e}")

        _end_card()


    # --- Fees ---
    elif item == "💰 My Fees & Payments":                
        render_fee_management(
            sid=user["student_id"], 
            available_years=["2023-24", "2024-25", "2025-26"]
        )

        # --- Cafeteria ---
    elif item == "🥗 Daily Menu":
        _render_card("🥗 Daily Menu")
        try:
            cur.execute("SELECT item_name,price FROM cafeteria_menu WHERE available=1")
            rows = cur.fetchall()
            if rows:
                df = pd.DataFrame(rows,columns=["Item","Price (₹)"])
                st.dataframe(df,use_container_width=True)
            else:
                st.info("No menu items available.")
        except:
            st.error("Error fetching cafeteria menu")
        _end_card()

    # --- Transport ---
    elif item == "🚌 Transport Info":
        _render_card("🚌 Transport Info")
        try:
            # optional: ensure route schema has in-charge fields
            conn = get_connection()
            _ensure_transport_schema(conn)  # no-op if already present
            cur = conn.cursor()

            sid_int = user.get("id")
            sid_legacy = user.get("student_id")

            query = """
            SELECT
                COALESCE(r.route_name, st.route_name)                  AS route_name,
                st.pickup_point,
                st.drop_point,
                COALESCE(r.driver_name,  st.driver_name)               AS driver_name,
                COALESCE(r.driver_contact, st.driver_phone)            AS driver_phone,
                r.vehicle_number,
                r.timing,
                r.incharge_name,
                r.incharge_phone
            FROM student_transport st
            LEFT JOIN transport_routes r ON r.id = st.fk_route_id
            WHERE (st.fk_student_id = ?)
               OR (st.student_id    = ?)
            LIMIT 1
            """
            cur.execute(query, (sid_int, sid_legacy))
            row = cur.fetchone()
            conn.close()

            if row:
                (route_name, pickup_point, drop_point,
                 driver_name, driver_phone,
                 vehicle_number, timing,
                 incharge_name, incharge_phone) = row

                c1, c2 = st.columns(2)
                with c1:
                    if route_name:     st.markdown(f"**Route:** {route_name}")
                    if pickup_point:   st.markdown(f"**Pickup point:** {pickup_point}")
                    if drop_point:     st.markdown(f"**Drop point:** {drop_point}")

                with c2:
                    if vehicle_number: st.markdown(f"**Bus / Vehicle #:** {vehicle_number}")
                    if timing:         st.markdown(f"**Timing:** {timing}")

                    if driver_name or driver_phone:
                        tel = f"tel:{driver_phone}" if driver_phone else "#"
                        st.markdown(
                            f"**Driver:** {driver_name or '-'} "
                            f"{f'([Call]({tel}))' if driver_phone else ''}"
                        )

                    if incharge_name or incharge_phone:
                        tel2 = f"tel:{incharge_phone}" if incharge_phone else "#"
                        st.markdown(
                            f"**Transport In-charge:** {incharge_name or '-'} "
                            f"{f'([Call]({tel2}))' if incharge_phone else ''}"
                        )
            else:
                st.info("No transport details found.")
        except Exception as e:
            st.error(f"Error fetching transport info: {e}")
        _end_card()

    
    #📍 Live Bus Tracking
    elif item == "📍 Live Bus Tracking":
        _render_card("📍 Live Bus Tracking")
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=10_000, key="bus_refresh")  # refresh every 10s
        try:
            conn = get_connection()
            cur = conn.cursor()
            sid_int = user.get("id")
            sid_legacy = user.get("student_id")

            cur.execute("""
                SELECT st.bus_lat, st.bus_lon
                FROM student_transport st
                WHERE (st.fk_student_id = ?)
                   OR (st.student_id    = ?)
                LIMIT 1
            """, (sid_int, sid_legacy))
            row = cur.fetchone()
            conn.close()

            if row and row[0] and row[1]:
                df_map = pd.DataFrame({"lat": [row[0]], "lon": [row[1]]})
                st.map(df_map, zoom=12)
            else:
                st.info("Live location not available.")
        except Exception as e:
            st.error(f"Error fetching live location: {e}")
        _end_card()

    # --- Receipts ---
    elif item == "📜 Receipts":
        _render_card("📜 Receipts")
        render_receipts(user)   # call function to show receipts
        
    #Live Bus Tracking
    elif item == "📍 Live Bus Tracking":
        _render_card("📍 Live Bus Tracking")
        try:
            cur.execute("SELECT bus_lat,bus_lon FROM student_transport WHERE student_id=?",(sid,))
            row = cur.fetchone()
            if row and row[0] and row[1]:
                df = pd.DataFrame({"lat":[row[0]],"lon":[row[1]]})
                st.map(df, zoom=12)
            else:
                st.info("Bus location not available.Please check if coordinates are in DB.")
        except:
            st.error("Error fetching bus location: {e}")
        _end_card()
        
    
    #AI Tutor
    elif item == "🤖 AI Tutor (24/7)":
        st.subheader("🤖 AI Tutor (24/7)")

        # Initialize chat history
        if "ai_tutor_history" not in st.session_state:
            st.session_state.ai_tutor_history = []

        # Show chat history
        for chat in st.session_state.ai_tutor_history:
            with st.chat_message(chat["role"]):
                st.markdown(chat["content"])
                if "image" in chat and chat["image"]:
                    st.image(chat["image"], caption="Visual aid")
                if "video" in chat and chat["video"]:
                    st.video(chat["video"])

        # Input box
        user_input = st.chat_input("Ask me anything...")
        if user_input:
            # Append user message
            st.session_state.ai_tutor_history.append({"role": "user", "content": user_input})

            # Show spinner while AI + video response is being fetched
            with st.spinner("🤖 Thinking and searching videos..."):
                # AI response (text + optional image)
                response_text, image_url = ai_tutor_response(user_input)

                # Video: curated list first, fallback → YouTube API
                video_url = get_video_url(user_input)

            # Show AI response
            with st.chat_message("ai"):
                st.markdown(response_text)
                if image_url:
                    st.image(image_url, caption="Visual aid")
                if video_url:
                    st.video(video_url)

            # Save AI response in history
            st.session_state.ai_tutor_history.append({
                "role": "ai",
                "content": response_text,
                "image": image_url,
                "video": video_url
            })

            st.rerun()

        # Clear chat button
        if st.button("🧹 Clear Chat"):
            st.session_state.ai_tutor_history = []
            st.rerun()

    
    # 📤 Submit Assignments (AI Checked)
    elif item == "📤 Submit Assignments (AI Checked)":
        _render_card("📤 Submit Assignments (AI Checked)")

        # --- Fetch homework for student's class & section ---
        cur.execute("""
            SELECT id, due_date, subject, description, title
            FROM assignments
            WHERE class=? AND section=?
            ORDER BY timestamp DESC
        """, (user.get("class"), user.get("section")))
        rows = cur.fetchall()

        if rows:
            # --- Let student pick exactly ONE assignment ---
            assignment_map = {
                f"{due} — {subj} ({title or 'Homework'})": (aid, due, subj, desc, title)
                for aid, due, subj, desc, title in rows
            }
            choice = st.radio("📚 Select Assignment", list(assignment_map.keys()))
            aid, due, subj, desc, title = assignment_map[choice]

            # --- Assignment details ---
            st.markdown(f"### 📖 {subj} — Due: {due}")
            st.write(f"**Homework:** {desc or '(no description)'}")

            # --- Check if already submitted ---
            cur.execute("""
                SELECT file_path, submitted_at
                FROM assignment_submissions
                WHERE assignment_id=? AND student_id=?
            """, (aid, user["id"]))
            submission = cur.fetchone()

            if submission:   # ✅ make sure it exists
                st.success(f"✅ Submitted on {submission[1]}")

                if submission[0] and os.path.exists(submission[0]):
                    with open(submission[0], "rb") as f:
                        file_bytes = f.read()

                    st.download_button(
                        "📂 Download your submission",
                        data=file_bytes,
                        file_name=os.path.basename(submission[0]),
                        mime="application/pdf" if submission[0].lower().endswith(".pdf") else None
                    )           
            else:
                # No submission yet → show upload options
                st.markdown("#### 📂 Upload / 📸 Capture")

                # --- Option 1: Camera Input ---
                photo = st.camera_input("📸 Take a photo of your homework", key=f"camera_{aid}")

                # --- Option 2: File Uploader ---
                uploaded = st.file_uploader(
                    "Or upload file (image/pdf)",
                    type=["jpg", "jpeg", "png", "pdf"],
                    key=f"upload_{aid}"
                )

                # If student submitted either option
                if photo or uploaded:
                    if photo:
                        fname = f"assignment_{aid}_{user['id']}_camera.jpg"
                        save_path = os.path.join(UPLOAD_DIR, fname)
                        with open(save_path, "wb") as f:
                            f.write(photo.getbuffer())
                    else:
                        fname = f"assignment_{aid}_{user['id']}_{uploaded.name}"
                        save_path = os.path.join(UPLOAD_DIR, fname)
                        with open(save_path, "wb") as f:
                            f.write(uploaded.getbuffer())

                    # --- AI silent check (NOT shown to student) ---
                    ai_feedback = "AI review not available."
                    try:
                        completion = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You are a teacher assistant. Give short constructive feedback on the uploaded homework."},
                                {"role": "user", "content": f"Review this homework submission for: {desc or title}"}
                            ]
                        )
                        ai_feedback = completion.choices[0].message.content
                    except Exception as e:
                        ai_feedback = f"⚠️ AI feedback error: {str(e)}"

                    # --- Save submission ---
                    cur.execute("""
                        INSERT INTO assignment_submissions
                        (assignment_id, student_id, file_path, ai_feedback, submitted_at)
                        VALUES (?, ?, ?, ?, datetime('now'))
                    """, (aid, user["id"], save_path, ai_feedback))
                    conn.commit()

                    st.success("✅ Submission saved successfully!")
                    st.rerun()
        else:
            st.info("No assignments available right now.")

        _end_card()

    
    #📈 Performance Insights
    elif item == "📈 Performance Insights":
        _render_card("📈 Performance Insights")
        try:
            import altair as alt

            # --- Fetch Data ---
            # Marks
            cur.execute("SELECT subject, secured_marks, total_marks, exam_type FROM marks WHERE student_id=?", (sid,))
            marks_rows = cur.fetchall()
            
            # Attendance
            cur.execute("SELECT date, status FROM attendance WHERE student_id=?", (sid,))
            attendance_rows = cur.fetchall()

            # Assignments & Submissions
            cur.execute("SELECT id, subject, due_date FROM assignments WHERE class=? AND section=?", (user["class"], user["section"]))
            all_assignments = cur.fetchall()

            cur.execute("SELECT assignment_id, ai_feedback, submitted_at FROM assignment_submissions WHERE student_id=?", (sid,))
            submissions = cur.fetchall()

            # Homework
            cur.execute("SELECT id, subject, due_date FROM homework  WHERE class=? AND section=?", (user["class"], user["section"]))
            homework_rows = cur.fetchall()

            # --- Convert to DataFrames ---
            marks_df = pd.DataFrame(marks_rows, columns=["Subject","Secured","Max","Exam"]) if marks_rows else pd.DataFrame()
            attendance_df = pd.DataFrame(attendance_rows, columns=["Date","Status"]) if attendance_rows else pd.DataFrame()            
            assignments_df = pd.DataFrame(all_assignments, columns=["AssignmentID","Subject","DueDate"]) if all_assignments else pd.DataFrame()
            submissions_df = pd.DataFrame(submissions, columns=["AssignmentID","AI_Feedback","SubmittedAt"]) if submissions else pd.DataFrame()
            homework_df = pd.DataFrame(homework_rows, columns=["ID","Subject","DueDate"]) if homework_rows else pd.DataFrame()      

            # --- Basic Stats & Insights ---
            insights = {}

            # Attendance
            if not attendance_df.empty:
                total_days = len(attendance_df)
                present_days = (attendance_df["Status"]=="Present").sum()
                absent_days = (attendance_df["Status"]=="Absent").sum()
                late_days = (attendance_df["Status"]=="Late").sum()
                attendance_rate = (present_days/total_days)*100
                insights["attendance"] = f"Attendance rate is {attendance_rate:.1f}%."
            else:
                insights["attendance"] = "No attendance data available."

            # Marks
            if not marks_df.empty:
                marks_df["Percent"] = (marks_df["Secured"]/marks_df["Max"])*100
                avg_score = marks_df["Percent"].mean()
                best_subject = marks_df.loc[marks_df["Percent"].idxmax(),"Subject"]
                weak_subject = marks_df.loc[marks_df["Percent"].idxmin(),"Subject"]
                insights["marks"] = f"Average score: {avg_score:.1f}%. Strongest in {best_subject}, needs improvement in {weak_subject}."
            else:
                insights["marks"] = "No marks data available."

            # Assignments & Submissions
            if not assignments_df.empty:
                total_assignments = len(assignments_df)
                submitted_assignments = submissions_df["AssignmentID"].nunique() if not submissions_df.empty else 0
                submission_rate = (submitted_assignments / total_assignments) * 100
                if not submissions_df.empty:
                    avg_feedback_len = submissions_df["AI_Feedback"].str.len().mean()
                    quality = "Good" if avg_feedback_len and avg_feedback_len > 50 else "Average"
                else:
                    quality = "No submissions yet"
                insights["assignments"] = (
                    f"Assignments given: {total_assignments}, submitted: {submitted_assignments} "
                    f"({submission_rate:.1f}%). Quality: {quality}."
                )
            else:
                insights["assignments"] = "No assignments found for your class/section."

            # Homework
            if not homework_df.empty:
                total_hw = len(homework_df)
                insights["homework"] = f"{total_hw} homework tasks were assigned this term."
            else:
                insights["homework"] = "No homework assigned yet."

            # --- AI-style Summary ---
            summary_lines = ["📊 **Performance Insights**\n"]

            # Attendance Text
            if 'attendance_rate' in locals():
                if attendance_rate >= 85:
                    summary_lines.append(f"✅ **Attendance** → {attendance_rate:.1f}% 🟢 Good\nGreat job! Keep maintaining consistency.")
                elif attendance_rate >= 60:
                    summary_lines.append(f"✅ **Attendance** → {attendance_rate:.1f}% 🟡 Average\nTry to reduce absences for steady improvement.")
                else:
                    summary_lines.append(f"✅ **Attendance** → {attendance_rate:.1f}% 🔴 Poor\n⚠ Needs Improvement: Attend regularly to boost performance.")

            # Marks Text
            if not marks_df.empty:
                if avg_score >= 80:
                    perf_tag = "🟢 Excellent"
                elif avg_score >= 60:
                    perf_tag = "🟡 Average"
                else:
                    perf_tag = "🔴 Weak"

                summary_lines.append(
                    f"\n📚 **Marks** → Avg: {avg_score:.1f}% {perf_tag}\n"
                    f"📈 Strong in: {best_subject}.\n"
                    f"📉 Needs focus: {weak_subject}.\n"
                    f"👉 Tip: Focus extra time on {weak_subject}, while keeping up your strength in {best_subject}."
                )

            # Assignments Text
            if not assignments_df.empty:
                if submission_rate >= 80:
                    perf_tag = "🟢 Good"
                elif submission_rate > 0:
                    perf_tag = "🟡 Average"
                else:
                    perf_tag = "🔴 Poor"

                summary_lines.append(
                    f"\n📤 **Assignments** → {total_assignments} given, {submitted_assignments} submitted ({submission_rate:.1f}%) {perf_tag}\n"
                    f"{'Keep up the good work!' if submission_rate>=80 else 'Try submitting regularly to build practice.'}"
                )

            # Homework Text
            if not homework_df.empty:
                summary_lines.append(
                    f"\n📝 **Homework** → {total_hw} tasks assigned 🟡 Average\n"
                    f"Try to complete daily homework for steady improvement."
                )

            # Subject-wise Trends Text
            subject_trends = []
            if not marks_df.empty and "Exam" in marks_df.columns:
                marks_df["ExamDate"] = pd.to_datetime(marks_df["Exam"], errors="coerce") 
                for subj, group in marks_df.groupby("Subject"):
                    group = group.sort_values("ExamDate")
                    group["Percent"] = (group["Secured"] / group["Max"]) * 100
                    
                    if len(group) >= 2:
                        latest = group.iloc[-1]["Percent"]
                        prev = group.iloc[-2]["Percent"]
                        diff = latest - prev
                        if diff > 5:
                            trend = "📈 Improving"
                        elif diff < -5:
                            trend = "📉 Dropping"
                        else:
                            trend = "➡ Stable"
                        subject_trends.append(f"{subj}: {latest:.1f}% ({trend})")
                    else:
                        latest = group.iloc[-1]["Percent"]
                        subject_trends.append(f"{subj}: {latest:.1f}% (no previous data)")

            if subject_trends:
                summary_lines.append(
                    "\n📊 **Subject-wise Trends**\n" +
                    "\n".join([f"- {t}" for t in subject_trends])
                )

            # Display AI-style Summary
            st.markdown("\n".join(summary_lines))

            # --- 2x2 Layout for Charts ---
            row1_col1, row1_col2 = st.columns(2)
            row2_col1, row2_col2 = st.columns(2)

            # --- Row 1, Col 1: Attendance Bar & Pie ---
            if not attendance_df.empty:
                with row1_col1:
                    # st.subheader("Attendance Overview")
                    # att_chart = alt.Chart(attendance_df).mark_bar().encode(
                        # x=alt.X('Status:N', title='Status'),
                        # y=alt.Y('count():Q', title='Days'),
                        # color=alt.Color('Status:N',
                                        # scale=alt.Scale(domain=['Present','Absent','Late'],
                                                        # range=['#28a745','#dc3545','#ffc107']),
                                        # legend=alt.Legend(title="Status"))
                    # )
                    # st.altair_chart(att_chart, use_container_width=True)
                    # # Optional Pie Chart
                    att_summary = pd.DataFrame({
                        "Status": ["Present", "Absent", "Late"],
                        "Count": [present_days, absent_days, late_days]
                    })
                    st.subheader("**Attendance %**")
                    pie_chart = alt.Chart(att_summary).mark_arc().encode(
                        theta='Count:Q',
                        color=alt.Color('Status:N', scale=alt.Scale(domain=['Present','Absent','Late'],
                                                                    range=['#28a745','#dc3545','#ffc107'])),
                        tooltip=['Status','Count']
                    )
                    st.altair_chart(pie_chart, use_container_width=True)

            # --- Row 1, Col 2: Subject-wise Average Marks ---
            if not marks_df.empty:
                with row1_col2:
                    st.subheader("Subject-wise Average Marks")
                    marks_summary = marks_df.groupby("Subject")["Percent"].mean().reset_index()
                    

                    # Correct color assignment using a new column
                    def mark_color(p):
                        if p >= 80:
                            return "#28a745"  # Green
                        elif p >= 60:
                            return "#ffc107"  # Yellow
                        else:
                            return "#dc3545"  # Red

                    marks_summary["Color"] = marks_summary["Percent"].apply(mark_color)

                    marks_chart = alt.Chart(marks_summary).mark_bar().encode(
                        x='Subject:N',
                        y='Percent:Q',
                        color=alt.Color('Color:N', scale=None),  # use exact hex colors
                        tooltip=['Subject','Percent']
                    )
                    st.altair_chart(marks_chart, use_container_width=True)

            # --- Row 2, Col 1: Assignments Submission ---
            if not assignments_df.empty:
                with row2_col1:
                    st.subheader("Assignments Submission")
                    submission_df = pd.DataFrame({
                        "Status": ["Submitted", "Pending"],
                        "Count": [submitted_assignments, total_assignments-submitted_assignments]
                    })
                    assign_chart = alt.Chart(submission_df).mark_bar().encode(
                        x='Status:N',
                        y='Count:Q',
                        color=alt.Color('Status:N', scale=alt.Scale(domain=['Submitted','Pending'],
                                                                    range=['#28a745','#dc3545'])),
                        tooltip=['Status','Count']
                    )
                    st.altair_chart(assign_chart, use_container_width=True)

            # --- Row 2, Col 2: Subject-wise Trends Over Time ---
            if not marks_df.empty and "ExamDate" in marks_df.columns:
                with row2_col2:
                    st.subheader("Subject-wise Trends Over Time")

                    # Ensure ExamDate is valid datetime
                    marks_df["ExamDate"] = pd.to_datetime(marks_df["Exam"], errors='coerce')
                    marks_df = marks_df.dropna(subset=["ExamDate"])  # remove invalid dates

                    trend_chart = alt.Chart(marks_df).mark_line(point=True).encode(
                        x=alt.X('ExamDate:T', title='Exam Date'),
                        y=alt.Y('Percent:Q', title='Score'),
                        color='Subject:N',
                        tooltip=['Subject','Percent','ExamDate']
                    ).properties(height=300)
                    st.altair_chart(trend_chart, use_container_width=True)


        except Exception as e:
            st.error(f"Error generating insights: {e}")

        _end_card()


import streamlit as st
from math import sqrt

# ---------- Text color helper ----------
def _get_text_color(bg_hex: str) -> str:
    """Return black/white depending on background brightness."""
    bg_hex = bg_hex.lstrip("#")
    r, g, b = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
    brightness = sqrt(0.299*r**2 + 0.587*g**2 + 0.114*b**2)
    return "#000000" if brightness > 150 else "#FFFFFF"


# ---------- CSS Injector ----------
def _inject_button_css(scope_id: str, color: str):
    tcolor = _get_text_color(color)
    st.markdown(f"""
    <style>
    div#{scope_id} button,
    div#{scope_id} div[data-testid="stButton"] > button,
    div#{scope_id} div.stButton > button {{
        width: 100% !important;
        background-color: {color} !important;
        color: {tcolor} !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 10px 14px !important;
        margin: 6px 0 12px 0 !important;
        transition: filter .15s ease, transform .02s ease;
        box-shadow: 0 2px 6px rgba(0,0,0,.15) !important;
    }}
    div#{scope_id} button:hover {{
        filter: brightness(90%) !important;
    }}
    div#{scope_id} button:active {{
        transform: translateY(1px) !important;
    }}
    </style>
    """, unsafe_allow_html=True)


# ---------- Render Dashboard ----------
# Helper: tile button
def _tile(label: str, color: str, key: str):
    return st.button(str(label), key=key, use_container_width=True)



def render_student_dashboard(groups: dict):
    
    # If a sub-item is active, do nothing here (content will be rendered by app.py)
    if st.session_state.get("item"):
        return
        
    _student_topbar() # header + logo + logout + single back control
    st.session_state.setdefault("group", None)
    st.session_state.setdefault("item", None)
    

    # If no group selected yet → show main groups
    if not st.session_state.get("group"):
        group_names = list(groups.keys())
        cols_per_row = 3
        st.markdown("<div id='tiles'>", unsafe_allow_html=True)
        for start in range(0, len(group_names), cols_per_row):
            cols = st.columns([1,1,1], gap="large")
            for i, gname in enumerate(group_names[start:start+cols_per_row]):
                gdata = groups.get(gname, {})
                with cols[i]:
                    if _tile(gname, gdata.get("color", "#2563eb"), key=f"group-{gname}"):
                        st.session_state["group"] = gname
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Else → show sub-group tiles for the selected group
    sel_group = st.session_state["group"]
    gdata = groups.get(sel_group, {})
    items = gdata.get("items", [])

    st.markdown("#### Select a section")
    st.markdown("<div id='tiles'>", unsafe_allow_html=True)
    cols_per_row = 3
    for start in range(0, len(items), cols_per_row):
        cols = st.columns([1,1,1], gap="large")
        for i, raw_item in enumerate(items[start:start+cols_per_row]):
            # Normalize label/color
            item_label = None
            item_color = gdata.get("color", "#2563eb")
            if isinstance(raw_item, str):
                item_label = raw_item
            elif isinstance(raw_item, (tuple, list)):
                if len(raw_item) >= 1: item_label = str(raw_item[0])
                if len(raw_item) >= 2 and isinstance(raw_item[1], str): item_color = raw_item[1]
            elif isinstance(raw_item, dict):
                item_label = str(raw_item.get("label") or raw_item.get("name") or "Unnamed")
                if isinstance(raw_item.get("color"), str): item_color = raw_item["color"]
            else:
                item_label = str(raw_item)

            with cols[i]:
                if _tile(item_label, item_color, key=f"sub-{sel_group}-{item_label}"):
                    st.session_state["item"] = item_label
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

