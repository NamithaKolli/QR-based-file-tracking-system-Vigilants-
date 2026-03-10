# 📂 QRTrack – QR-Based Physical File Tracking System
**Team Vigilants – Group 15**

---

## 🚀 COMPLETE SETUP GUIDE (Step by Step)

---

### STEP 1 — Install Python

**What:** Python is the language this app runs on.
**Where:** Your computer (Windows/Mac/Linux)
**How:**

1. Go to: https://www.python.org/downloads/
2. Download **Python 3.11** or newer
3. During install on Windows → ✅ Check "Add Python to PATH"
4. Verify in terminal/cmd:
   ```
   python --version
   ```

---

### STEP 2 — Download the Project

**What:** Get all the project files onto your computer.
**Where:** Any folder on your computer (e.g., Desktop)
**How:**

Option A – If you have the ZIP:
1. Unzip the folder → you'll see `app.py`, `templates/`, etc.

Option B – If using Git:
```
git clone <your-repo-url>
cd qr-file-tracker
```

---

### STEP 3 — Create a Virtual Environment

**What:** An isolated Python environment so packages don't conflict.
**Where:** Inside the project folder (where `app.py` is)
**How:**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

You'll see `(venv)` appear in your terminal — that means it worked.

---

### STEP 4 — Install Required Packages

**What:** Install Flask (web framework) and QR code library.
**Where:** In the terminal, inside your project folder with venv active
**How:**

```bash
pip install -r requirements.txt
```

This installs:
- `flask` – the web server
- `qrcode[pil]` – generates QR code images
- `pillow` – image processing

---

### STEP 5 — Run the App

**What:** Start the local web server.
**Where:** Terminal inside the project folder
**How:**

```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
```

---

### STEP 6 — Open in Browser

**What:** Access the web app.
**Where:** Any web browser on the same computer
**How:**

Open: **http://127.0.0.1:5000**

Login with:
- Username: `admin`
- Password: `admin123`

---

### STEP 7 — Create Staff Accounts

**What:** Add accounts for each staff member.
**Where:** Admin panel → Users (top-left sidebar)
**How:**

1. Click **Users** in the sidebar
2. Fill in: Full Name, Username, Password, Department, Role
3. Click **Create User**

Roles:
- **Admin** – full access (create files, manage users)
- **Staff** – can scan and view history
- **Viewer** – read-only access

---

### STEP 8 — Create Your First File

**What:** Register a physical file in the system and get its QR code.
**Where:** Create New File page
**How:**

1. Click **New File** in the sidebar
2. Enter:
   - File ID: e.g. `CS-2024-001` (unique identifier)
   - File Name: e.g. `Budget Approval – CS Dept`
   - Department: Select from dropdown
   - Priority: Normal / High / Urgent / Confidential
3. Click **Generate QR Code**
4. Download the QR image → print it → stick it on the physical file

---

### STEP 9 — Scan Files

**What:** Record file movement whenever it moves between people/departments.
**Where:** Scan QR page
**How:**

1. Click **Scan QR** in sidebar
2. Click **Start Camera Scanner** → point at the file's QR code
   (OR type the File ID manually)
3. Select action:
   - **Check In** – receiving/returning the file
   - **Check Out** – taking the file
   - **Transfer** – permanently moving to another department
4. Add optional notes
5. Click **Submit Action**

---

### STEP 10 — View History

**What:** See the complete audit trail of any file.
**Where:** History page
**How:**

1. Click **History** in sidebar
2. Type the File ID
3. See full timeline: who had it, when, what action

---

## 📁 Project File Structure

```
qr-file-tracker/
│
├── app.py                    ← Main Flask app (all routes & logic)
├── requirements.txt          ← Python packages to install
├── database.db               ← Auto-created SQLite database
│
├── templates/                ← HTML pages
│   ├── base.html             ← Shared layout (sidebar, nav)
│   ├── login.html            ← Login page
│   ├── index.html            ← Dashboard
│   ├── create.html           ← Create new file + QR generation
│   ├── scan.html             ← QR scanner + check in/out
│   ├── history.html          ← File movement history
│   ├── files.html            ← All files list
│   └── users.html            ← User management (admin only)
│
└── static/
    └── qrcodes/              ← Generated QR code images (PNG)
```

---

## 🌐 Run on Network (Other Devices on Same WiFi)

So phones can scan via camera on the same network:

Change the last line of `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
```

Find your computer's IP:
- Windows: `ipconfig` → look for IPv4
- Mac/Linux: `ifconfig` → look for inet

Others on same WiFi open: `http://YOUR-IP:5000`

---

## 🐛 Common Issues & Fixes

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: flask` | Run `pip install -r requirements.txt` |
| `Port 5000 already in use` | Change port: `app.run(port=5001)` |
| Camera not working on scan page | Use HTTPS or run on `localhost` (not IP) |
| QR code not showing after create | Check `static/qrcodes/` folder exists |
| `database.db` errors | Delete `database.db` and restart the app |

---

## 📱 Making Camera Work on Mobile

Browsers only allow camera access on:
- `localhost` (local machine)
- HTTPS connections

For mobile access, use **ngrok** for free HTTPS tunnel:
```bash
pip install pyngrok
# Then in a new terminal:
ngrok http 5000
```
Use the `https://...ngrok.io` URL on mobile.

---

## 🔮 Future Additions (From Your Presentation)

- [ ] Email/SMS alerts for delayed file returns
- [ ] Digital file request system
- [ ] QR codes on cabinets for location tracking
- [ ] Workshop/event approval tracking
- [ ] Hostel leave request tracking
- [ ] Export to PDF/Excel reports
