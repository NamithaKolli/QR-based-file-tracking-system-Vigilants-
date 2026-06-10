QRTrack – QR-Based Physical File Tracking System
QRTrack is a lightweight web application designed to digitally track the movement and lifecycle of physical files across departments using QR codes. It replaces manual file registers with a scannable, traceable, and transparent workflow system.
The system allows staff to create files, generate QR codes, scan them during transfers, and maintain a complete history of file movement and status. Built specifically for IIITDM Kancheepuram's administrative and academic departments.

Features

Role-based login system

Admin
Staff
Viewer (read-only access)


File Creation with QR Code

Generates QR codes for every file (stored as base64 — no filesystem required)
Unique file IDs for tracking
File priority levels: Normal, High, Urgent
Optional description and due date at creation
Add document sub-parts (e.g. invoices, memos, reports) at creation time


QR Code Scanning Interface

Check-in / Check-out / Transfer files
Receiver name tracking per action
Due date assignment on checkout
Double-checkout prevention (file must be checked in before checking out again)
Track file movement across departments


File Parts Tracking

Attach multiple document parts to a single file
33 supported part types mapped per department (e.g. Purchase Invoice, NOC, Grade Sheet, Research Paper)
View parts grouped by type
Add new parts to existing files


File Lifecycle Tracking

Created
Review
Approved
Closed


Overdue File Detection

Files past their due date are flagged automatically
Overdue popup shown on login dashboard
Email notification sent to logged-in user on login if overdue files exist


Email Notification System

Action emails sent on checkout, check-in, transfer, and file creation
HTML-formatted emails with file details, handler, receiver, and due date
Sent asynchronously (non-blocking) via Gmail SMTP
Configurable via environment variables


Movement History

Complete audit trail of file movement between departments


Admin User Management

Create and manage users
Assign roles and departments
Delete users
Email field per user for notifications


Department-based file tracking

12 departments pre-configured for IIITDM Kancheepuram


Cloud / PostgreSQL Support

Dual database support: SQLite (local) and PostgreSQL (cloud/production)
Auto-detects DATABASE_URL environment variable
QR codes stored as base64 in the database (no file storage needed on cloud)




System Architecture
Frontend

HTML
CSS
Jinja2 Templates

Backend

Python (Flask)

Database

SQLite (local development)
PostgreSQL (cloud deployment)

Libraries

Flask
qrcode
Pillow
psycopg2
gunicorn
smtplib (built-in)


Project Structure
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
│   ├── users.html
│   ├── file_parts.html
│   └── view_part.html
│
├── static/
│   └── qrcodes/
│
└── README.md

Software Requirements
Recommended versions:
SoftwareVersionPython3.10 – 3.12Flask3.0+SQLiteBuilt into PythonpipLatest
Python can be installed from: https://www.python.org/downloads/

Installation
Clone the repository:
git clone https://github.com/NamithaKolli/QR-based-file-tracking-system-Vigilants-.git
cd QR-based-file-tracking-system-Vigilants-

Install Dependencies
Install required Python packages:
pip install -r requirements.txt
Required libraries include:

Flask
qrcode[pil]
psycopg2-binary
gunicorn


Running the Application
Windows
Open Command Prompt or PowerShell inside the project folder.
Run:
python app.py
or
py app.py
The application will start at:
http://127.0.0.1:5000

Linux / Ubuntu / macOS
Open a terminal inside the project directory and run:
python3 app.py
Then open the application in a browser:
http://127.0.0.1:5000

Default Login
A default admin account is created automatically on first run.
UsernamePasswordadminadmin123
It is recommended to change the admin password after first login.

Create Account

Choose the create account option from the login page.
New accounts are assigned the Viewer role by default (read-only access).
The administrator must upgrade a user's role to Staff or Admin to grant write access.


Typical Workflow

Admin creates user accounts and assigns departments.
Staff log in to the system.
A file is created and assigned a unique file ID.
A QR code is generated for the file.
Document sub-parts (invoices, memos, etc.) can be attached to the file.
Departments scan the QR code when checking out or transferring the file.
The receiver's name is recorded at each step.
The system logs every movement and stage of the file.
Overdue files are flagged on the dashboard and notified via email.


Example File Lifecycle
Created → Review → Approved → Closed
Each stage can be updated during QR scanning.

Email Notifications (Optional Setup)
QRTrack can send email alerts for file actions and overdue reminders. To enable, set the following environment variables:
VariableDescriptionMAIL_EMAILGmail address to send fromMAIL_PASSWORDApp password for the Gmail accountMAIL_SERVERSMTP server (default: smtp.gmail.com)MAIL_PORTSMTP port (default: 587)SECRET_KEYFlask session secret keyDATABASE_URLPostgreSQL URL (for cloud deployment)
Emails are sent asynchronously and will fail silently if not configured.

Security Features

Password hashing using SHA-256
Role-based access control (Admin / Staff / Viewer)
Admin-only user management
Session-based authentication
Viewer role enforced at route level — all write actions blocked


Departments (Pre-configured for IIITDM Kancheepuram)

Computer Science Engineering
Electronics and Communication Engineering
Mechanical Engineering
Smart Manufacturing
Sciences and Humanities
Design (SIDI)
Administration
Library
Hostel Office
Finance
Student Affairs
Research


Contributors

Namitha Sai Kolli
Gogineni Gouthami
Surapaneni Aasritha Sri Varshini
Ravipati Vishnu Tejaswini
Jeevani Yalamanchilli
Maramganty Mayukha


License
This project is intended for educational and academic purposes.

Future Improvements

Time-based push notifications
Priority order for urgent files
Automated file approval workflows
Deployment to cloud servers (Render / Railway)
Mobile-friendly interface
Search and filter on the files page
File archiving and soft-delete
