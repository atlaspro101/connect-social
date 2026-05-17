import sqlite3
import hashlib
from datetime import datetime

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

try:
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Создание таблиц
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        bio TEXT,
        birthday TEXT,
        gender TEXT,
        avatar TEXT,
        banner TEXT,
        is_admin INTEGER DEFAULT 0,
        last_seen TIMESTAMP,
        created_at TIMESTAMP
    )''')
    
    # Другие таблицы...
    
    # Создание админа
    admin_pass = hash_password("fastyk26tyr")
    c.execute("INSERT OR IGNORE INTO users (username, password, full_name, is_admin, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
              ("taranka", admin_pass, "Admin Taranka", 1, datetime.now(), datetime.now()))
    
    conn.commit()
    conn.close()
    print("✅ Database setup complete.")
except Exception as e:
    print(f"Error: {e}")