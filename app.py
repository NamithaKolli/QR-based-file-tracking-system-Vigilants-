from flask import Flask, render_template, request, redirect, jsonify, session, flash
import os
from datetime import datetime, timezone, timedelta
from functools import wraps

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    """Return current datetime string in IST, formatted cleanly."""
    return datetime.now(IST).strftime("%d/%m/%Y %H:%M")
import hashlib
import qrcode
import io
import base64
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DATABASE_URL = os.environ.get("DATABASE_URL")

try:
    import psycopg2
    import psycopg2.extras
    USE_POSTGRES = bool(DATABASE_URL)
except ImportError:
    USE_POSTGRES = False

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "qrtrack_secret_key_2024")
app.config["SESSION_COOKIE_SIZE"] = 4096

os.makedirs("static/qrcodes", exist_ok=True)

# ── Institutional constants (IIITDM Kancheepuram) ────────────────
DEPARTMENTS = [
    "Computer Science Engineering",
    "Electronics and Communication Engineering",
    "Mechanical Engineering",
    "Smart Manufacturing",
    "Sciences and Humanities",
    "Design (SIDI)",
    "Administration",
    "Library",
    "Hostel Office",
    "Finance",
    "Student Affairs",
    "Research",
]

# Realistic academic/administrative document sub-part types
PART_TYPES = [
    "Purchase Invoice",
    "Approval Letter",
    "Quotation",
    "Project Report",
    "Official Memo",
    "Application Form",
    "Payment Receipt",
    "Lab Report",
    "Course Outline",
    "Grade Sheet",
    "Examination Paper",
    "NOC",
    "Sanction Letter",
    "Budget Estimate",
    "Audit Report",
    "Research Paper",
    "Ethics Clearance",
    "Grant Sanction",
    "Equipment Requisition",
    "Collaboration Agreement",
    "Allotment Letter",
    "Complaint Form",
    "Maintenance Request",
    "Fee Receipt",
    "Scholarship Letter",
    "Bonafide Certificate",
    "Grievance Form",
    "Event Proposal",
    "Book Request",
    "Acquisition List",
    "Due Notice",
    "Inventory Record",
    "Other",
]

# Department-specific part type mappings (used in create/file_parts templates)
DEPT_PARTS = {
    "Computer Science Engineering":             ["Purchase Invoice","Approval Letter","Quotation","Project Report","Lab Report","Course Outline","Grade Sheet","Examination Paper","NOC","Official Memo","Application Form","Payment Receipt","Other"],
    "Electronics and Communication Engineering":["Purchase Invoice","Approval Letter","Quotation","Project Report","Lab Report","Course Outline","Grade Sheet","Examination Paper","NOC","Official Memo","Application Form","Payment Receipt","Other"],
    "Mechanical Engineering":                   ["Purchase Invoice","Approval Letter","Quotation","Project Report","Lab Report","Course Outline","Grade Sheet","Examination Paper","NOC","Official Memo","Equipment Requisition","Payment Receipt","Other"],
    "Smart Manufacturing":                      ["Purchase Invoice","Approval Letter","Quotation","Project Report","Lab Report","Course Outline","Grade Sheet","Examination Paper","NOC","Official Memo","Equipment Requisition","Payment Receipt","Other"],
    "Sciences and Humanities":                  ["Purchase Invoice","Approval Letter","Quotation","Research Paper","Lab Report","Course Outline","Grade Sheet","Examination Paper","NOC","Official Memo","Application Form","Payment Receipt","Other"],
    "Design (SIDI)":                            ["Purchase Invoice","Approval Letter","Quotation","Project Report","Lab Report","Course Outline","Grade Sheet","Examination Paper","NOC","Official Memo","Application Form","Payment Receipt","Other"],
    "Administration":                           ["Official Memo","Approval Letter","Sanction Letter","Budget Estimate","Audit Report","Purchase Invoice","Quotation","Payment Receipt","NOC","Application Form","Other"],
    "Library":                                  ["Book Request","Acquisition List","Due Notice","Inventory Record","Purchase Invoice","Quotation","Payment Receipt","Official Memo","Other"],
    "Hostel Office":                            ["Allotment Letter","Complaint Form","Maintenance Request","Fee Receipt","Official Memo","Application Form","Payment Receipt","NOC","Other"],
    "Finance":                                  ["Budget Estimate","Audit Report","Purchase Invoice","Quotation","Payment Receipt","Sanction Letter","Grant Sanction","Official Memo","Approval Letter","Other"],
    "Student Affairs":                          ["Application Form","Scholarship Letter","Bonafide Certificate","Grievance Form","Event Proposal","NOC","Approval Letter","Official Memo","Payment Receipt","Other"],
    "Research":                                 ["Project Report","Research Paper","Grant Sanction","Ethics Clearance","Equipment Requisition","Collaboration Agreement","Purchase Invoice","Quotation","Payment Receipt","Official Memo","Other"],
}

# ──────────────────────────── DATABASE ────────────────────────────

def get_db():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect("database.db", timeout=10)
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        return conn

def db_execute(conn, sql, params=()):
    if USE_POSTGRES:
        sql = sql.replace("?", "%s")
    c = conn.cursor()
    c.execute(sql, params)
    return c

def db_fetchone(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(row) if USE_POSTGRES else row

def db_fetchall(cursor):
    rows = cursor.fetchall()
    return [dict(r) for r in rows] if USE_POSTGRES else rows

def init_db():
    conn = get_db()

    if USE_POSTGRES:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'staff',
            full_name TEXT,
            department TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS files (
            file_id TEXT PRIMARY KEY,
            file_name TEXT,
            department TEXT,
            created_date TEXT,
            status TEXT DEFAULT 'active',
            stage TEXT DEFAULT 'created',
            priority TEXT DEFAULT 'normal',
            description TEXT,
            due_date TEXT,
            qr_base64 TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS movements (
            id SERIAL PRIMARY KEY,
            file_id TEXT,
            department TEXT,
            person TEXT,
            receiver TEXT,
            action TEXT,
            in_time TEXT,
            out_time TEXT,
            notes TEXT,
            due_date TEXT,
            reminder_status TEXT DEFAULT 'none'
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS file_parts (
            id SERIAL PRIMARY KEY,
            file_id TEXT NOT NULL,
            part_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            created_by TEXT,
            created_date TEXT
        )''')

        c.execute("ALTER TABLE movements ADD COLUMN IF NOT EXISTS due_date TEXT")
        c.execute("ALTER TABLE movements ADD COLUMN IF NOT EXISTS reminder_status TEXT DEFAULT 'none'")
        c.execute("ALTER TABLE movements ADD COLUMN IF NOT EXISTS receiver TEXT")
        c.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS due_date TEXT")
        c.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS qr_base64 TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT")
        
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("""INSERT INTO users (username, password, role, full_name, department)
                     VALUES (%s,%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING""",
                  ("admin", admin_pw, "admin", "Administrator", "Admin"))
        conn.commit()
        conn.close()
    else:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'staff',
            full_name TEXT,
            department TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS files (
            file_id TEXT PRIMARY KEY,
            file_name TEXT,
            department TEXT,
            created_date TEXT,
            status TEXT DEFAULT 'active',
            stage TEXT DEFAULT 'created',
            priority TEXT DEFAULT 'normal',
            description TEXT,
            due_date TEXT,
            qr_base64 TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            department TEXT,
            person TEXT,
            receiver TEXT,
            action TEXT,
            in_time TEXT,
            out_time TEXT,
            notes TEXT,
            due_date TEXT,
            reminder_status TEXT DEFAULT 'none'
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS file_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            part_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            created_by TEXT,
            created_date TEXT
        )''')
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT OR IGNORE INTO users (username, password, role, full_name, department) VALUES (?,?,?,?,?)",
                  ("admin", admin_pw, "admin", "Administrator", "Admin"))
        try:
            c.execute("ALTER TABLE users ADD COLUMN email TEXT")
        except:
            pass
        try:
            c.execute("ALTER TABLE movements ADD COLUMN receiver TEXT")
        except:
            pass
        conn.commit()
        conn.close()

init_db()

# ──────────────────────── QR CODE HELPER ────────────────────────

def generate_qr_base64(file_id):
    """Returns a base64 data URI — no filesystem needed on the cloud."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(file_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

# ──────────────────────────── AUTH ────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect("/")
        return f(*args, **kwargs)
    return decorated

def staff_required(f):
    """Blocks viewer-role users from write actions."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        if session.get("role") == "viewer":
            flash("Viewers have read-only access. This action is not permitted.", "error")
            return redirect("/")
        return f(*args, **kwargs)
    return decorated

def _smtp_send(to_email: str, subject: str, body: str):
    """Internal helper — sends via Gmail SMTP using env credentials.
    Works locally and on any server; fails silently if unconfigured."""
    MAIL_EMAIL    = os.environ.get("MAIL_EMAIL")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_SERVER   = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT     = int(os.environ.get("MAIL_PORT", "587"))
    if not MAIL_EMAIL or not MAIL_PASSWORD or not to_email:
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = MAIL_EMAIL
        msg["To"]      = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        if MAIL_PORT == 465:
            server = smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT, timeout=10)
        else:
            server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
        server.login(MAIL_EMAIL, MAIL_PASSWORD)
        server.sendmail(MAIL_EMAIL, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"[QRTrack] Email error: {e}")

def send_overdue_email(to_email, overdue_files):
    rows = "".join(
        f"<tr style='border-bottom:1px solid #eee'>"
        f"<td style='padding:8px 12px;font-family:monospace;color:#0ea5e9'>{f['file_id']}</td>"
        f"<td style='padding:8px 12px'>{f['file_name']}</td>"
        f"<td style='padding:8px 12px;color:#ef4444'>{f['due_date']}</td>"
        f"<td style='padding:8px 12px'>{f['person']}</td></tr>"
        for f in overdue_files
    )
    body = f"""
    <div style='font-family:sans-serif;max-width:600px;margin:auto'>
      <h2 style='color:#ef4444'>⚠️ QRTrack — {len(overdue_files)} Overdue File(s)</h2>
      <p>The following files are past their due date. Please take action.</p>
      <table style='width:100%;border-collapse:collapse;background:#f8fafc;border-radius:8px'>
        <thead><tr style='background:#1e293b;color:#fff'>
          <th style='padding:10px 12px;text-align:left'>File ID</th>
          <th style='padding:10px 12px;text-align:left'>Name</th>
          <th style='padding:10px 12px;text-align:left'>Due Date</th>
          <th style='padding:10px 12px;text-align:left'>Handler</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <p style='margin-top:16px;color:#64748b;font-size:13px'>
        Log in to <strong>QRTrack</strong> to resolve these items.
      </p>
    </div>"""
    _smtp_send(to_email, f"QRTrack — {len(overdue_files)} Overdue File(s)", body)

def send_action_email(action: str, file_id: str, file_name: str,
                      sender: str, receiver: str, department: str,
                      notes: str = "", due_date: str = "",
                      receiver_email: str = "", sender_email: str = ""):
    """Send notification email on checkout / transfer / checkin actions."""
    action_labels = {
        "checkout": ("📤 File Checked Out", "#f59e0b"),
        "checkin":  ("📥 File Checked In",  "#10b981"),
        "transfer": ("🔄 File Transferred",  "#00d4ff"),
        "created":  ("✦ File Created",       "#a78bfa"),
    }
    label, colour = action_labels.get(action, (f"Action: {action}", "#64748b"))

    body = f"""
    <div style='font-family:sans-serif;max-width:560px;margin:auto'>
      <div style='background:{colour};padding:14px 24px;border-radius:10px 10px 0 0'>
        <h2 style='color:#fff;margin:0;font-size:18px'>{label}</h2>
      </div>
      <div style='background:#f8fafc;padding:20px 24px;border:1px solid #e2e8f0;border-radius:0 0 10px 10px'>
        <table style='width:100%;border-collapse:collapse;font-size:14px'>
          <tr><td style='padding:6px 0;color:#64748b;width:130px'>File ID</td>
              <td style='padding:6px 0;font-family:monospace;color:#0ea5e9;font-weight:700'>{file_id}</td></tr>
          <tr><td style='padding:6px 0;color:#64748b'>File Name</td>
              <td style='padding:6px 0;font-weight:600'>{file_name}</td></tr>
          <tr><td style='padding:6px 0;color:#64748b'>Department</td>
              <td style='padding:6px 0'>{department}</td></tr>
          <tr><td style='padding:6px 0;color:#64748b'>Actioned By</td>
              <td style='padding:6px 0'>{sender}</td></tr>
          <tr><td style='padding:6px 0;color:#64748b'>Receiver</td>
              <td style='padding:6px 0'>{receiver or "—"}</td></tr>
          {"<tr><td style='padding:6px 0;color:#64748b'>Due Date</td><td style='padding:6px 0;color:#f59e0b'>" + due_date + "</td></tr>" if due_date else ""}
          {"<tr><td style='padding:6px 0;color:#64748b'>Notes</td><td style='padding:6px 0;color:#64748b;font-style:italic'>" + notes + "</td></tr>" if notes else ""}
        </table>
        <p style='margin-top:16px;font-size:12px;color:#94a3b8'>
          This is an automated notification from <strong>QRTrack</strong> — IIITDM Kancheepuram.
        </p>
      </div>
    </div>"""

    subject = f"QRTrack: {label} — {file_id}"
    import threading
    for addr in {receiver_email, sender_email} - {"", None}:
        t = threading.Thread(target=_smtp_send, args=(addr, subject, body), daemon=True)
        t.start()

# ──────────────────────────── ROUTES ────────────────────────────

@app.route("/")
@login_required
def index():
    conn = get_db()

    c = db_execute(conn, "SELECT COUNT(*) as cnt FROM files")
    total_files = db_fetchone(c)["cnt"]

    c = db_execute(conn, "SELECT COUNT(*) as cnt FROM movements WHERE out_time IS NULL")
    checked_out = db_fetchone(c)["cnt"]

    c = db_execute(conn, "SELECT COUNT(DISTINCT department) as cnt FROM files")
    departments = db_fetchone(c)["cnt"]

    # Recent activity
    c = db_execute(conn, """SELECT m.*, f.file_name FROM movements m
                             JOIN files f ON m.file_id = f.file_id
                             ORDER BY m.id DESC LIMIT 8""")
    recent = db_fetchall(c)

    # Overdue: past due date AND no checkin recorded after the checkout
    if USE_POSTGRES:
        c = db_execute(conn, """
            SELECT f.file_id, f.file_name, m.person, m.due_date
            FROM movements m
            JOIN files f ON f.file_id = m.file_id
            WHERE m.action = 'checkout'
            AND m.due_date IS NOT NULL
            AND m.due_date::date < CURRENT_DATE
            AND NOT EXISTS (
                SELECT 1 FROM movements m2
                WHERE m2.file_id = m.file_id
                AND m2.action = 'checkin'
                AND m2.id > m.id
            )
        """)
    else:
        today_ist = datetime.now(IST).strftime("%Y-%m-%d")
        c = db_execute(conn, """
            SELECT f.file_id, f.file_name, m.person, m.due_date
            FROM movements m
            JOIN files f ON f.file_id = m.file_id
            WHERE m.action = 'checkout'
            AND m.due_date IS NOT NULL
            AND date(m.due_date) < date(?)
            AND NOT EXISTS (
                SELECT 1 FROM movements m2
                WHERE m2.file_id = m.file_id
                AND m2.action = 'checkin'
                AND m2.id > m.id
            )
        """, (today_ist,))
    overdue = db_fetchall(c)

    conn.close()
    overdue_popup = session.pop("overdue_popup", None)
    return render_template("index.html",
        total_files=total_files,
        checked_out=checked_out,
        departments=departments,
        recent=recent,
        overdue=overdue,
        overdue_popup=overdue_popup
    )

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        conn = get_db()
        c = db_execute(conn, "SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = db_fetchone(c)
        conn.close()
        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]
            session["department"] = user["department"]

            # Check for overdue files and notify
            conn = get_db()
            if USE_POSTGRES:
                c = conn.cursor()
                c.execute("""
                    SELECT f.file_id, f.file_name, m.person, m.due_date
                    FROM movements m JOIN files f ON f.file_id = m.file_id
                    WHERE m.action = 'checkout'
                    AND m.due_date IS NOT NULL
                    AND m.due_date::date < CURRENT_DATE
                    AND NOT EXISTS (
                        SELECT 1 FROM movements m2
                        WHERE m2.file_id = m.file_id
                        AND m2.action = 'checkin'
                        AND m2.id > m.id
                    )
                """)
                overdue = [dict(r) for r in c.fetchall()]
            else:
                c = conn.cursor()
                today_ist = datetime.now(IST).strftime("%Y-%m-%d")
                overdue = c.execute("""
                    SELECT f.file_id, f.file_name, m.person, m.due_date
                    FROM movements m JOIN files f ON f.file_id = m.file_id
                    WHERE m.action = 'checkout'
                    AND m.due_date IS NOT NULL
                    AND date(m.due_date) < date(?)
                    AND NOT EXISTS (
                        SELECT 1 FROM movements m2
                        WHERE m2.file_id = m.file_id
                        AND m2.action = 'checkin'
                        AND m2.id > m.id
                    )
                """, (today_ist,)).fetchall()
                overdue = [dict(r) for r in overdue]
            conn.close()

            if overdue:
                session["overdue_popup"] = [
                    {"file_id": f["file_id"], "file_name": f["file_name"],
                    "due_date": str(f["due_date"]), "person": f["person"]}
                    for f in overdue
                ]
                # Send email in background thread so login doesn't slow down
                if user.get("email"):
                    import threading
                    thread = threading.Thread(
                        target=send_overdue_email,
                        args=(user["email"], overdue)
                    )
                    thread.daemon = True
                    thread.start()

            return redirect("/")
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username  = request.form["username"].strip()
        password  = hashlib.sha256(request.form["password"].encode()).hexdigest()
        full_name = request.form["full_name"].strip()
        dept      = request.form["department"].strip()
        email     = request.form.get("email", "").strip()
        conn = get_db()
        try:
            if USE_POSTGRES:
                c = conn.cursor()
                c.execute("INSERT INTO users (username,password,role,full_name,department,email) VALUES (%s,%s,%s,%s,%s,%s)",
                          (username, password, "viewer", full_name, dept,email))
            else:
                c = conn.cursor()
                c.execute("INSERT INTO users (username,password,role,full_name,department,email) VALUES (?,?,?,?,?,?)",
                          (username, password, "viewer", full_name, dept,email))
            conn.commit()
            flash("Account created successfully. Please login.", "success")
            return redirect("/login")
        except Exception:
            flash("Username already exists.", "error")
        finally:
            conn.close()
    return render_template("signup.html", departments=DEPARTMENTS)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/create", methods=["GET","POST"])
@login_required
@staff_required
def create():
    if request.method == "POST":
        file_id   = request.form["file_id"].strip().upper()
        file_name = request.form["file_name"].strip()
        dept      = request.form["department"].strip()
        priority  = request.form.get("priority", "normal")
        desc      = request.form.get("description", "").strip()
        person    = session["full_name"]

        conn = get_db()
        c = db_execute(conn, "SELECT file_id FROM files WHERE file_id=?", (file_id,))
        existing = db_fetchone(c)
        if existing:
            conn.close()
            flash(f"File ID '{file_id}' already exists.", "error")
            return render_template("create.html", qr_b64=None, departments=DEPARTMENTS, part_types=PART_TYPES, dept_parts=DEPT_PARTS)

        # Generate QR as base64 (works on cloud — no filesystem needed)
        qr_b64 = generate_qr_base64(file_id)

        # Also save to disk locally for backward compat
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(file_id)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0f172a", back_color="white")
            img.save(f"static/qrcodes/{file_id}.png")
        except Exception:
            pass

        now = now_ist()

        if USE_POSTGRES:
            c = conn.cursor()
            c.execute("""
                INSERT INTO files (file_id,file_name,department,created_date,status,stage,priority,description,qr_base64)
                VALUES (%s,%s,%s,%s,'active','created',%s,%s,%s)
            """, (file_id, file_name, dept, now, priority, desc, qr_b64))
            c.execute("""
                INSERT INTO movements (file_id,department,person,action,in_time)
                VALUES (%s,%s,%s,'created',%s)
            """, (file_id, dept, person, now))
        else:
            c = conn.cursor()
            c.execute("""
                INSERT INTO files (file_id,file_name,department,created_date,status,stage,priority,description,qr_base64)
                VALUES (?,?,?,?,'active','created',?,?,?)
            """, (file_id, file_name, dept, now, priority, desc, qr_b64))
            c.execute("""
                INSERT INTO movements (file_id,department,person,action,in_time)
                VALUES (?,?,?,'created',?)
            """, (file_id, dept, person, now))

        # --- Insert any parts submitted alongside the file ---
        part_types   = request.form.getlist("part_type[]")
        part_titles  = request.form.getlist("part_title[]")
        part_descs   = request.form.getlist("part_desc[]")
        for pt, ptitle, pdesc in zip(part_types, part_titles, part_descs):
            pt     = pt.strip()
            ptitle = ptitle.strip()
            if not pt or not ptitle:
                continue
            if USE_POSTGRES:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO file_parts (file_id,part_type,title,description,created_by,created_date) VALUES (%s,%s,%s,%s,%s,%s)",
                    (file_id, pt, ptitle, pdesc.strip(), person, now)
                )
            else:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO file_parts (file_id,part_type,title,description,created_by,created_date) VALUES (?,?,?,?,?,?)",
                    (file_id, pt, ptitle, pdesc.strip(), person, now)
                )

        conn.commit()
        conn.close()

        flash(f"File '{file_name}' created successfully!", "success")
        return render_template("create.html", qr_b64=qr_b64, file_id=file_id,
                               file_name=file_name, departments=DEPARTMENTS, part_types=PART_TYPES, dept_parts=DEPT_PARTS)

    return render_template("create.html", qr_b64=None, departments=DEPARTMENTS, part_types=PART_TYPES, dept_parts=DEPT_PARTS)

@app.route("/scan", methods=["GET","POST"])
@login_required
@staff_required
def scan():
    if request.method == "POST":
        file_id  = request.form["file_id"].strip().upper()
        action   = request.form["action"]
        stage    = request.form.get("stage")
        notes    = request.form.get("notes", "")
        person   = session["full_name"]   # the person performing the action
        dept     = session["department"]
        # receiver = whoever physically takes/gets the file (submitted via form)
        # For checkin: the person scanning IS the receiver (they're getting the file back)
        # For checkout/transfer: explicitly entered in the form
        receiver_raw = request.form.get("receiver", "").strip()
        receiver = receiver_raw if receiver_raw else person

        conn = get_db()
        c = db_execute(conn, "SELECT * FROM files WHERE file_id=?", (file_id,))
        file_row = db_fetchone(c)
        if not file_row:
            conn.close()
            flash(f"File ID '{file_id}' not found.", "error")
            return render_template("scan.html", departments=DEPARTMENTS)

        # ── Checkout lock: prevent double-checkout ──
        if action == "checkout":
            c = db_execute(conn, """
                SELECT id FROM movements
                WHERE file_id=? AND action='checkout'
                AND NOT EXISTS (
                    SELECT 1 FROM movements m2
                    WHERE m2.file_id = movements.file_id
                    AND m2.action = 'checkin'
                    AND m2.id > movements.id
                )
                ORDER BY id DESC LIMIT 1
            """, (file_id,))
            already_out = db_fetchone(c)
            if already_out:
                conn.close()
                flash(f"File '{file_id}' is already checked out. It must be checked in before checking out again.", "error")
                return render_template("scan.html", departments=DEPARTMENTS)

        now = now_ist()

        # Fetch receiver email and sender email for notifications
        c = db_execute(conn, "SELECT email FROM users WHERE full_name=?", (person,))
        sender_row   = db_fetchone(c)
        sender_email = sender_row["email"] if sender_row and sender_row.get("email") else ""

        if USE_POSTGRES:
            c = conn.cursor()
            if action == "checkin":
                # On check-in the person logging in is the receiver
                c.execute("UPDATE movements SET out_time=%s WHERE file_id=%s AND out_time IS NULL", (now, file_id))
                c.execute("""INSERT INTO movements (file_id,department,person,receiver,action,in_time,notes)
                             VALUES (%s,%s,%s,%s,'checkin',%s,%s)""",
                          (file_id, dept, person, person, now, notes))
            elif action == "checkout":
                due_date = request.form.get("due_date", "").strip() or None
                c.execute("SELECT id FROM movements WHERE file_id=%s AND out_time IS NULL ORDER BY id DESC LIMIT 1", (file_id,))
                open_row = c.fetchone()
                if open_row:
                    c.execute("UPDATE movements SET out_time=%s WHERE id=%s", (now, dict(open_row)["id"]))
                c.execute("""INSERT INTO movements (file_id,department,person,receiver,action,in_time,notes,due_date)
                             VALUES (%s,%s,%s,%s,'checkout',%s,%s,%s)""",
                          (file_id, dept, person, person, now, notes, due_date))
                if due_date:
                    c.execute("UPDATE files SET due_date=%s WHERE file_id=%s", (due_date, file_id))
            elif action == "transfer":
                new_dept = request.form.get("new_department", dept)
                # Receiver = person in destination dept (logged-in user initiates, destination records them)
                c.execute("UPDATE movements SET out_time=%s WHERE file_id=%s AND out_time IS NULL", (now, file_id))
                c.execute("""INSERT INTO movements (file_id,department,person,receiver,action,in_time,notes)
                             VALUES (%s,%s,%s,%s,'transfer',%s,%s)""",
                          (file_id, new_dept, person, person,
                           now, f"Transferred to {new_dept}. {notes}".strip()))
                c.execute("UPDATE files SET department=%s WHERE file_id=%s", (new_dept, file_id))
            if stage:
                c.execute("UPDATE files SET stage=%s WHERE file_id=%s", (stage, file_id))
        else:
            c = conn.cursor()
            if action == "checkin":
                c.execute("UPDATE movements SET out_time=? WHERE file_id=? AND out_time IS NULL", (now, file_id))
                c.execute("""INSERT INTO movements (file_id,department,person,receiver,action,in_time,notes)
                             VALUES (?,?,?,?,'checkin',?,?)""",
                          (file_id, dept, person, person, now, notes))
            elif action == "checkout":
                due_date = request.form.get("due_date", "").strip() or None
                open_row = c.execute("SELECT id FROM movements WHERE file_id=? AND out_time IS NULL ORDER BY id DESC LIMIT 1", (file_id,)).fetchone()
                if open_row:
                    c.execute("UPDATE movements SET out_time=? WHERE id=?", (now, open_row["id"]))
                c.execute("""INSERT INTO movements (file_id,department,person,receiver,action,in_time,notes,due_date)
                             VALUES (?,?,?,?,'checkout',?,?,?)""",
                          (file_id, dept, person, person, now, notes, due_date))
                if due_date:
                    c.execute("UPDATE files SET due_date=? WHERE file_id=?", (due_date, file_id))
            elif action == "transfer":
                new_dept = request.form.get("new_department", dept)
                c.execute("UPDATE movements SET out_time=? WHERE file_id=? AND out_time IS NULL", (now, file_id))
                c.execute("""INSERT INTO movements (file_id,department,person,receiver,action,in_time,notes)
                             VALUES (?,?,?,?,'transfer',?,?)""",
                          (file_id, new_dept, person, person,
                           now, f"Transferred to {new_dept}. {notes}".strip()))
                c.execute("UPDATE files SET department=? WHERE file_id=?", (new_dept, file_id))
            if stage:
                c.execute("UPDATE files SET stage=? WHERE file_id=?", (stage, file_id))

        conn.commit()

        # Fire action email notification (non-blocking)
        due_date_str = request.form.get("due_date", "").strip() if action == "checkout" else ""
        new_dept_for_email = request.form.get("new_department", dept) if action == "transfer" else dept
        send_action_email(
            action=action,
            file_id=file_id,
            file_name=file_row.get("file_name", ""),
            sender=person,
            receiver=receiver,
            department=new_dept_for_email,
            notes=notes,
            due_date=due_date_str,
            sender_email=sender_email,
        )

        conn.close()
        flash(f"Action '{action}' recorded for file {file_id}.", "success")
        return redirect("/")
    return render_template("scan.html", departments=DEPARTMENTS)

@app.route("/history", methods=["GET","POST"])
@login_required
def history():
    records = None
    file_info = None
    file_id = request.form.get("file_id", "").strip().upper() if request.method == "POST" else ""
    if file_id:
        conn = get_db()
        c = db_execute(conn, "SELECT * FROM files WHERE file_id=?", (file_id,))
        file_info = db_fetchone(c)
        c = db_execute(conn, "SELECT * FROM movements WHERE file_id=? ORDER BY id DESC", (file_id,))
        records = db_fetchall(c)
        conn.close()
    return render_template("history.html", records=records, file_info=file_info, searched_id=file_id)

@app.route("/files")
@login_required
def all_files():
    conn = get_db()
    c = db_execute(conn, """SELECT f.*, m.person, m.action, m.in_time
                             FROM files f
                             LEFT JOIN movements m ON m.id = (
                                 SELECT MAX(id) FROM movements WHERE file_id = f.file_id
                             )
                             ORDER BY f.department, f.created_date DESC""")
    files = db_fetchall(c)

    # Determine checked-out status per file
    checked_out_ids = set()
    for f in files:
        fid = f["file_id"]
        c2 = db_execute(conn, """
            SELECT id FROM movements
            WHERE file_id=? AND action='checkout'
            AND NOT EXISTS (
                SELECT 1 FROM movements m2
                WHERE m2.file_id = movements.file_id
                AND m2.action = 'checkin'
                AND m2.id > movements.id
            )
            ORDER BY id DESC LIMIT 1
        """, (fid,))
        if db_fetchone(c2):
            checked_out_ids.add(fid)

    conn.close()

    # Group by department
    dept_groups = {}
    for f in files:
        dept = f.get("department") or "Unknown"
        f["is_checked_out"] = f["file_id"] in checked_out_ids
        dept_groups.setdefault(dept, []).append(f)

    return render_template("files.html", files=files, dept_groups=dept_groups)

@app.route("/users", methods=["GET","POST"])
@admin_required
def users():
    if request.method == "POST":
        username  = request.form["username"].strip()
        password  = hashlib.sha256(request.form["password"].encode()).hexdigest()
        role      = request.form["role"]
        full_name = request.form["full_name"].strip()
        dept      = request.form["department"].strip()
        email     = request.form.get("email", "").strip()
        conn = get_db()
        try:
            if USE_POSTGRES:
                c = conn.cursor()
                c.execute("INSERT INTO users (username,password,role,full_name,department,email) VALUES (%s,%s,%s,%s,%s,%s)",
                          (username, password, role, full_name, dept,email))
            else:
                c = conn.cursor()
                c.execute("INSERT INTO users (username,password,role,full_name,department,email) VALUES (?,?,?,?,?,?)",
                          (username, password, role, full_name, dept,email))
            conn.commit()
            flash(f"User '{username}' created!", "success")
        except Exception:
            flash("Username already exists.", "error")
        finally:
            conn.close()
    conn = get_db()
    c = db_execute(conn, "SELECT id, username, role, full_name, department,email FROM users")
    all_users = db_fetchall(c)
    conn.close()
    return render_template("users.html", users=all_users, departments=DEPARTMENTS)

@app.route("/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):
    conn = get_db()
    db_execute(conn, "DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("User deleted.", "success")
    return redirect("/users")

@app.route("/fileinfo/<file_id>")
@login_required
def fileinfo(file_id):
    conn = get_db()
    c = db_execute(conn, "SELECT * FROM files WHERE file_id=?", (file_id.upper(),))
    f = db_fetchone(c)
    c = db_execute(conn, "SELECT * FROM movements WHERE file_id=? ORDER BY id DESC LIMIT 1", (file_id.upper(),))
    m = db_fetchone(c)
    # Check if currently checked out
    c2 = db_execute(conn, """
        SELECT id FROM movements
        WHERE file_id=? AND action='checkout'
        AND NOT EXISTS (
            SELECT 1 FROM movements m2
            WHERE m2.file_id = movements.file_id
            AND m2.action = 'checkin'
            AND m2.id > movements.id
        )
        ORDER BY id DESC LIMIT 1
    """, (file_id.upper(),))
    is_checked_out = db_fetchone(c2) is not None
    conn.close()
    if not f:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "file_name": f["file_name"],
        "department": f["department"],
        "priority": f["priority"],
        "status": f["status"],
        "stage": f.get("stage", "created"),
        "person": m["person"] if m else "Unknown",
        "last_receiver": m["receiver"] if m and m.get("receiver") else (m["person"] if m else "Unknown"),
        "is_checked_out": is_checked_out
    })

@app.route("/file/<file_id>/add_part", methods=["POST"])
@login_required
@staff_required
def add_part(file_id):
    part_type   = request.form.get("part_type", "").strip()
    title       = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    created_by  = session["full_name"]
    now         = now_ist()

    if not part_type or not title:
        flash("Part type and title are required.", "error")
        return redirect(f"/file/{file_id}/parts")

    conn = get_db()
    if USE_POSTGRES:
        c = conn.cursor()
        c.execute(
            "INSERT INTO file_parts (file_id, part_type, title, description, created_by, created_date) VALUES (%s,%s,%s,%s,%s,%s)",
            (file_id, part_type, title, description, created_by, now)
        )
    else:
        c = conn.cursor()
        c.execute(
            "INSERT INTO file_parts (file_id, part_type, title, description, created_by, created_date) VALUES (?,?,?,?,?,?)",
            (file_id, part_type, title, description, created_by, now)
        )
    conn.commit()
    conn.close()
    flash(f"Part '{title}' added successfully.", "success")
    return redirect(f"/file/{file_id}/parts")

@app.route("/file/<file_id>/parts")
@login_required
def file_parts(file_id):
    conn = get_db()
    c = db_execute(conn, "SELECT * FROM files WHERE file_id=?", (file_id.upper(),))
    file_info = db_fetchone(c)
    if not file_info:
        conn.close()
        flash("File not found.", "error")
        return redirect("/files")

    c = db_execute(conn, "SELECT * FROM file_parts WHERE file_id=? ORDER BY id DESC", (file_id.upper(),))
    parts = db_fetchall(c)
    conn.close()

    # Group parts by type
    grouped = {}
    for p in parts:
        ptype = p["part_type"]
        grouped.setdefault(ptype, []).append(p)

    return render_template("file_parts.html", file_info=file_info, grouped=grouped,
                           all_parts=parts, part_types=PART_TYPES)

@app.route("/part/<int:part_id>")
@login_required
def view_part(part_id):
    conn = get_db()
    c = db_execute(conn, "SELECT * FROM file_parts WHERE id=?", (part_id,))
    part = db_fetchone(c)
    conn.close()
    if not part:
        flash("Part not found.", "error")
        return redirect("/files")
    return render_template("view_part.html", part=part)

@app.route("/api/users")
@login_required
def api_users():
    """Returns list of all registered users for the receiver quick-select in scan page."""
    conn = get_db()
    c = db_execute(conn, "SELECT full_name, department, role FROM users ORDER BY full_name")
    users = db_fetchall(c)
    conn.close()
    return jsonify({"users": users})

@app.route("/api/graph-data")
@login_required
def api_graph_data():
    """
    Returns department nodes and file nodes as JSON for the
    spider-web network graph on the /files page.
    """
    conn = get_db()

    # Fetch all files with their latest movement info
    c = db_execute(conn, """
        SELECT f.file_id, f.file_name, f.department, f.priority,
               f.status, f.stage, f.created_date,
               m.person, m.action
        FROM files f
        LEFT JOIN movements m ON m.id = (
            SELECT MAX(id) FROM movements WHERE file_id = f.file_id
        )
        ORDER BY f.department, f.created_date DESC
    """)
    files = db_fetchall(c)
    conn.close()

    # Build department summary
    dept_map = {}
    for f in files:
        dept = f.get("department") or "Unknown"
        if dept not in dept_map:
            dept_map[dept] = {"id": f"dept_{dept}", "name": dept, "file_count": 0}
        dept_map[dept]["file_count"] += 1

    # Build file node list
    file_nodes = [
        {
            "id":         f["file_id"],
            "name":       f["file_name"],
            "department": f.get("department") or "Unknown",
            "priority":   f.get("priority") or "normal",
            "action":     f.get("action") or "",
            "person":     f.get("person") or "—",
            "stage":      f.get("stage") or "created",
            "created":    f.get("created_date") or "",
        }
        for f in files
    ]

    return jsonify({
        "departments": list(dept_map.values()),
        "files":       file_nodes,
    })


@app.route("/print_all_qr")
@login_required
def print_all_qr():
    conn = get_db()
    c = db_execute(conn, "SELECT file_id, file_name, department, qr_base64 FROM files ORDER BY department, file_id")
    files = db_fetchall(c)
    conn.close()
    # Filter to only files that have QR codes stored
    files = [f for f in files if f.get("qr_base64")]
    return render_template("print_qr.html", files=files)

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)