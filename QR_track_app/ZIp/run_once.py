import sqlite3
conn = sqlite3.connect("database.db")
conn.execute("ALTER TABLE files ADD COLUMN stage TEXT DEFAULT 'created'")
conn.commit()
conn.close()