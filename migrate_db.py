import sqlite3
from datetime import datetime
import hashlib

def migrate_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Проверяем и добавляем недостающие колонки в таблицу users
    try:
        c.execute("ALTER TABLE users ADD COLUMN last_seen TIMESTAMP")
        print("✓ Добавлена колонка last_seen")
    except sqlite3.OperationalError:
        print("! Колонка last_seen уже существует")
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        print("✓ Добавлена колонка is_admin")
    except sqlite3.OperationalError:
        print("! Колонка is_admin уже существует")
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
        print("✓ Добавлена колонка is_banned")
    except sqlite3.OperationalError:
        print("! Колонка is_banned уже существует")
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN ban_until TIMESTAMP")
        print("✓ Добавлена колонка ban_until")
    except sqlite3.OperationalError:
        print("! Колонка ban_until уже существует")
    
    # Проверяем и добавляем недостающие колонки в таблицу posts
    try:
        c.execute("ALTER TABLE posts ADD COLUMN media_path TEXT")
        print("✓ Добавлена колонка media_path в posts")
    except sqlite3.OperationalError:
        print("! Колонка media_path уже существует в posts")
    
    try:
        c.execute("ALTER TABLE posts ADD COLUMN media_type TEXT")
        print("✓ Добавлена колонка media_type в posts")
    except sqlite3.OperationalError:
        print("! Колонка media_type уже существует в posts")
    
    try:
        c.execute("ALTER TABLE posts ADD COLUMN likes INTEGER DEFAULT 0")
        print("✓ Добавлена колонка likes в posts")
    except sqlite3.OperationalError:
        print("! Колонка likes уже существует в posts")
    
    # Создаем таблицу bans если её нет
    c.execute('''CREATE TABLE IF NOT EXISTS bans
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  admin_id INTEGER,
                  user_id INTEGER,
                  reason TEXT,
                  ban_until TIMESTAMP,
                  created_at TIMESTAMP,
                  FOREIGN KEY(admin_id) REFERENCES users(id),
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    print("✓ Таблица bans создана")
    
    # Обновляем last_seen для существующих пользователей
    c.execute("UPDATE users SET last_seen = ? WHERE last_seen IS NULL", (datetime.now(),))
    print("✓ Обновлены last_seen для существующих пользователей")
    
    # Создаем админа taranka если его нет
    admin_pass = hashlib.sha256("fastyk26tyr".encode()).hexdigest()
    
    # Проверяем существует ли админ
    c.execute("SELECT id FROM users WHERE username = 'taranka'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, full_name, is_admin, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                  ("taranka", admin_pass, "Admin Taranka", 1, datetime.now(), datetime.now()))
        print("✓ Админ создан: taranka / fastyk26tyr")
    else:
        # Обновляем существующего админа
        c.execute("UPDATE users SET is_admin = 1, password = ? WHERE username = 'taranka'", (admin_pass,))
        print("✓ Админ обновлен: taranka / fastyk26tyr")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Миграция базы данных завершена успешно!")

if __name__ == '__main__':
    migrate_database()