
Here we have attached all links for our new project QR file tracking sysytem.
# QRTrack – QR-Based Physical File Tracking System

QRTrack is a lightweight web application designed to digitally track the movement and lifecycle of physical files across departments using QR codes. It replaces manual file registers with a scannable, traceable, and transparent workflow system.

The system allows staff to create files, generate QR codes, scan them during transfers, and maintain a complete history of file movement and status.

---

# Features

* Role-based login system

  * Admin
  * Staff
  * Viewer

* File Creation with QR Code

  * Generates QR codes for every file
  * Unique file IDs for tracking

* QR Code Scanning Interface

  * Check-in / Check-out / Transfer files
  * Track file movement across departments

* File Lifecycle Tracking

  * Created
  * Review
  * Approved
  * Closed

* Movement History

  * Complete audit trail of file movement between departments

* Admin User Management

  * Create and manage users
  * Assign roles and departments

* Department-based file tracking

---

# System Architecture

Frontend

* HTML
* CSS
* Jinja2 Templates

Backend

* Python (Flask)

Database

* SQLite

Libraries

* Flask
* qrcode
* Pillow

---

# Project Structure

```
QRTrack/
│
├── app.py
├── database.db
├── requirements.txt
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── signup.html
│   ├── index.html
│   ├── create.html
│   ├── scan.html
│   ├── files.html
│   ├── history.html
│   └── users.html
│
├── static/
│   └── qrcodes/
│
└── README.md
```

---

# Software Requirements

Recommended versions:

| Software | Version           |
| -------- | ----------------- |
| Python   | 3.10 – 3.12       |
| Flask    | 3.0               |
| SQLite   | Built into Python |
| pip      | Latest            |

Python can be installed from:
https://www.python.org/downloads/

---

# Installation

Clone the repository:

```
git clone https://github.com/YOUR_USERNAME/qrtrack.git
cd qrtrack
```

---

# Install Dependencies

Install required Python packages:

```
pip install -r requirements.txt
```

Required libraries include:

* Flask
* qrcode
* Pillow

---

# Running the Application

## Windows

Open Command Prompt or PowerShell inside the project folder.

Run:

```
python app.py
```

or

```
py app.py
```

The application will start at:

```
http://127.0.0.1:5000
```

---

## Linux / Ubuntu / macOS

Open a terminal inside the project directory and run:

```
python3 app.py
```

Then open the application in a browser:

```
http://127.0.0.1:5000
```

---

# Create account

* Choose create account option.
* However, in real app any created account will not have access to all files unless given permission by the administrator
* We have not added that option for learners to access all features of app.


---

# Typical Workflow

1. Admin creates user accounts.
2. Staff log in to the system.
3. A file is created and assigned a unique file ID.
4. A QR code is generated for the file.
5. Departments scan the QR code when transferring the file.
6. The system logs every movement and stage of the file.

---

# Example File Lifecycle

```
Created → Review → Approved → Closed
```

Each stage can be updated during QR scanning.

---

# Security Features

* Password hashing using SHA-256
* Role-based access control
* Admin-only user management
* Session-based authentication

---

# Contributors

* Namitha Sai Kolli
* Gogineni Gouthami
* Surapaneni Aasritha Sri Varshini
* Ravipati Vishnu Tejaswini
* Jeevani Yalamanchilli

---

# License

This project is intended for educational and academic purposes.

---

# Future Improvements

* Time based notifications
* Priority order for urgent files
* Email notifications for file transfers
* Automated file approval workflows
* Deployment to cloud servers
* Mobile-friendly interface

