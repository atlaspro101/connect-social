import sqlite3
import hashlib
from datetime import datetime

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def setup_database():
    DATABASE_PATH = 'users.db'
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Удаляем старые таблицы, если есть (для чистой установки)
    c.execute('DROP TABLE IF EXISTS users')
    c.execute('DROP TABLE IF EXISTS posts')
    c.execute('DROP TABLE IF EXISTS comments')
    c.execute('DROP TABLE IF EXISTS post_likes')
    c.execute('DROP TABLE IF EXISTS followers')
    
    # Таблица пользователей
    c.execute('''CREATE TABLE users (
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
    
    # Таблица постов
    c.execute('''CREATE TABLE posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        media_path TEXT,
        media_type TEXT,
        likes INTEGER DEFAULT 0,
        created_at TIMESTAMP
    )''')
    
    # Таблица комментариев
    c.execute('''CREATE TABLE comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        content TEXT,
        created_at TIMESTAMP
    )''')
    
    # Таблица лайков
    c.execute('''CREATE TABLE post_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        UNIQUE(post_id, user_id)
    )''')
    
    # Таблица подписчиков
    c.execute('''CREATE TABLE followers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id INTEGER,
        following_id INTEGER,
        created_at TIMESTAMP,
        UNIQUE(follower_id, following_id)
    )''')
    
    # Создаем админа
    admin_pass = hash_password("fastyk26tyr")
    c.execute('''INSERT INTO users (username, password, full_name, is_admin, created_at, last_seen) 
                 VALUES (?, ?, ?, ?, ?, ?)''',
              ("taranka", admin_pass, "Admin Taranka", 1, datetime.now(), datetime.now()))
    
    conn.commit()
    conn.close()
    
    print("✅ База данных успешно создана!")
    print("📝 Данные для входа:")
    print("   Логин: taranka")
    print("   Пароль: fastyk26tyr")

if __name__ == '__main__':
    setup_database()