from flask import Flask, render_template, request, redirect, jsonify, session, url_for, flash
import sqlite3
import qrcode
import os
from datetime import datetime
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = "qrtrack_secret_key_2024"

# Create folders
os.makedirs("static/qrcodes", exist_ok=True)

# ──────────────────────────── DATABASE ────────────────────────────

def get_db():
    conn = sqlite3.connect("database.db", timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
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
        description TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT,
        department TEXT,
        person TEXT,
        action TEXT,
        in_time TEXT,
        out_time TEXT,
        notes TEXT
    )''')

    # Seed admin user
    admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password, role, full_name, department) VALUES (?, ?, ?, ?, ?)",
              ("admin", admin_pw, "admin", "Administrator", "Admin"))

    conn.commit()
    conn.close()

init_db()

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

# ──────────────────────────── ROUTES ────────────────────────────

@app.route("/")
@login_required
def index():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM files")
    total_files = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(*) as cnt FROM movements WHERE out_time IS NULL")
    checked_out = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(DISTINCT department) as cnt FROM files")
    departments = c.fetchone()["cnt"]
    c.execute("""SELECT m.*, f.file_name FROM movements m
                 JOIN files f ON m.file_id = f.file_id
                 ORDER BY m.id DESC LIMIT 8""")
    recent = c.fetchall()
    conn.close()
    return render_template("index.html",
        total_files=total_files,
        checked_out=checked_out,
        departments=departments,
        recent=recent
    )

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        conn.close()
        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]
            session["department"] = user["department"]
            return redirect("/")
        flash("Invalid username or password.", "error")
    return render_template("login.html")

    

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/create", methods=["GET","POST"])
@login_required
def create():
    if request.method == "POST":
        file_id   = request.form["file_id"].strip().upper()
        file_name = request.form["file_name"].strip()
        dept      = request.form["department"].strip()
        priority  = request.form.get("priority", "normal")
        desc      = request.form.get("description", "").strip()
        person    = session["full_name"]

        conn = get_db()
        c = conn.cursor()
        existing = c.execute("SELECT file_id FROM files WHERE file_id=?", (file_id,)).fetchone()
        if existing:
            conn.close()
            flash(f"File ID '{file_id}' already exists.", "error")
            return render_template("create.html", qr_path=None)

        c.execute("INSERT INTO files VALUES (?, ?, ?, ?, 'active', 'created', ?, ?)",
                  (file_id, file_name, dept, str(datetime.now()), priority, desc))
        c.execute("INSERT INTO movements (file_id, department, person, action, in_time, out_time) VALUES (?, ?, ?, 'created', ?, NULL)",
                  (file_id, dept, person, str(datetime.now())))
        conn.commit()
        conn.close()

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(file_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="white")
        qr_path = f"static/qrcodes/{file_id}.png"
        img.save(qr_path)

        flash(f"File '{file_name}' created successfully!", "success")
        return render_template("create.html", qr_path=qr_path, file_id=file_id, file_name=file_name)

    return render_template("create.html", qr_path=None)

@app.route("/scan", methods=["GET","POST"])
@login_required
def scan():
    if request.method == "POST":
        file_id = request.form["file_id"].strip().upper()
        action  = request.form["action"]
        stage = request.form.get("stage")
        notes   = request.form.get("notes", "")
        person  = session["full_name"]
        dept    = session["department"]

        conn = get_db()
        c = conn.cursor()
        file_row = c.execute("SELECT * FROM files WHERE file_id=?", (file_id,)).fetchone()
        if not file_row:
            conn.close()
            flash(f"File ID '{file_id}' not found.", "error")
            return render_template("scan.html")

        now = str(datetime.now())
        if action == "checkin":
            c.execute("UPDATE movements SET out_time=? WHERE file_id=? AND out_time IS NULL",
                      (now, file_id))
            c.execute("INSERT INTO movements (file_id, department, person, action, in_time, notes) VALUES (?, ?, ?, 'checkin', ?, ?)",
                      (file_id, dept, person, now, notes))
        elif action == "checkout":
            open_row = c.execute("SELECT id FROM movements WHERE file_id=? AND out_time IS NULL ORDER BY id DESC LIMIT 1", (file_id,)).fetchone()
            if open_row:
                c.execute("UPDATE movements SET out_time=? WHERE id=?", (now, open_row["id"]))
            c.execute("INSERT INTO movements (file_id, department, person, action, in_time, notes) VALUES (?, ?, ?, 'checkout', ?, ?)",
                      (file_id, dept, person, now, notes))
        elif action == "transfer":
            new_dept = request.form.get("new_department", dept)
            c.execute("UPDATE movements SET out_time=? WHERE file_id=? AND out_time IS NULL",
                      (now, file_id))
            c.execute("INSERT INTO movements (file_id, department, person, action, in_time, notes) VALUES (?, ?, ?, 'transfer', ?, ?)",
                      (file_id, new_dept, person, now, f"Transferred to {new_dept}. {notes}"))
            c.execute("UPDATE files SET department=? WHERE file_id=?", (new_dept, file_id))

        if stage:
            c.execute("UPDATE files SET stage=? WHERE file_id=?", (stage, file_id))

        conn.commit()
        conn.close()
        flash(f"Action '{action}' recorded for file {file_id}.", "success")
        return redirect("/")
    return render_template("scan.html")

@app.route("/history", methods=["GET","POST"])
@login_required
def history():
    records = None
    file_info = None
    file_id = request.form.get("file_id", "").strip().upper() if request.method == "POST" else ""
    if file_id:
        conn = get_db()
        file_info = conn.execute("SELECT * FROM files WHERE file_id=?", (file_id,)).fetchone()
        records = conn.execute("SELECT * FROM movements WHERE file_id=? ORDER BY id DESC", (file_id,)).fetchall()
        conn.close()
    return render_template("history.html", records=records, file_info=file_info, searched_id=file_id)

@app.route("/files")
@login_required
def all_files():
    conn = get_db()
    files = conn.execute("SELECT f.*, m.person, m.action, m.in_time FROM files f LEFT JOIN movements m ON m.id = (SELECT MAX(id) FROM movements WHERE file_id = f.file_id) ORDER BY f.created_date DESC").fetchall()
    conn.close()
    return render_template("files.html", files=files)

@app.route("/users", methods=["GET","POST"])
@admin_required
def users():
    if request.method == "POST":
        username  = request.form["username"].strip()
        password  = hashlib.sha256(request.form["password"].encode()).hexdigest()
        role      = request.form["role"]
        full_name = request.form["full_name"].strip()
        dept      = request.form["department"].strip()
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password, role, full_name, department) VALUES (?, ?, ?, ?, ?)",
                         (username, password, role, full_name, dept))
            conn.commit()
            flash(f"User '{username}' created!", "success")
        except sqlite3.IntegrityError:
            flash("Username already exists.", "error")
        conn.close()
    conn = get_db()
    all_users = conn.execute("SELECT id, username, role, full_name, department FROM users").fetchall()
    conn.close()
    return render_template("users.html", users=all_users)

@app.route("/fileinfo/<file_id>")
@login_required
def fileinfo(file_id):
    conn = get_db()
    f = conn.execute("SELECT * FROM files WHERE file_id=?", (file_id.upper(),)).fetchone()
    m = conn.execute("SELECT * FROM movements WHERE file_id=? ORDER BY id DESC LIMIT 1", (file_id.upper(),)).fetchone()
    conn.close()
    if not f:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "file_name": f["file_name"],
        "department": f["department"],
        "priority": f["priority"],
        "status": f["status"],
        "person": m["person"] if m else "Unknown"
    })

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
