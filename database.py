import sqlite3
from datetime import datetime, timedelta
import hashlib
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'users.db')

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Таблица users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        full_name TEXT,
        bio TEXT,
        birthday TEXT,
        gender TEXT,
        avatar TEXT,
        banner TEXT,
        is_admin INTEGER DEFAULT 0,
        is_premium INTEGER DEFAULT 0,
        is_verified INTEGER DEFAULT 0,
        is_private INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        experience INTEGER DEFAULT 0,
        twofa_secret TEXT,
        theme_color TEXT DEFAULT 'purple',
        theme_background TEXT DEFAULT 'gradient',
        chat_wallpaper TEXT DEFAULT '',
        animations_enabled INTEGER DEFAULT 1,
        last_seen TIMESTAMP,
        created_at TIMESTAMP
    )''')
    
    # Таблица постов
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        media_path TEXT,
        media_type TEXT,
        likes INTEGER DEFAULT 0,
        created_at TIMESTAMP
    )''')
    
    # Таблица комментариев
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        content TEXT,
        created_at TIMESTAMP
    )''')
    
    # Таблица лайков постов
    c.execute('''CREATE TABLE IF NOT EXISTS post_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        UNIQUE(post_id, user_id)
    )''')
    
    # Таблица подписчиков
    c.execute('''CREATE TABLE IF NOT EXISTS followers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id INTEGER,
        following_id INTEGER,
        created_at TIMESTAMP,
        UNIQUE(follower_id, following_id)
    )''')
    
    # Таблица чатов
    c.execute('''CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_id INTEGER,
        user2_id INTEGER,
        is_group INTEGER DEFAULT 0,
        group_name TEXT,
        group_avatar TEXT,
        created_at TIMESTAMP,
        UNIQUE(user1_id, user2_id)
    )''')
    
    # Таблица сообщений
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        sender_id INTEGER,
        receiver_id INTEGER,
        message TEXT,
        media_path TEXT,
        media_type TEXT,
        reply_to INTEGER DEFAULT 0,
        is_edited INTEGER DEFAULT 0,
        is_deleted INTEGER DEFAULT 0,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP,
        FOREIGN KEY(chat_id) REFERENCES chats(id)
    )''')
    
    # Таблица реакций на сообщения
    c.execute('''CREATE TABLE IF NOT EXISTS message_reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        user_id INTEGER,
        reaction TEXT,
        created_at TIMESTAMP,
        UNIQUE(message_id, user_id)
    )''')
    
    # Таблица блокировок
    c.execute('''CREATE TABLE IF NOT EXISTS blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blocker_id INTEGER,
        blocked_id INTEGER,
        created_at TIMESTAMP,
        UNIQUE(blocker_id, blocked_id)
    )''')
    
    # Таблица жалоб
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_id INTEGER,
        reported_id INTEGER,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP
    )''')
    
    # Таблица достижений
    c.execute('''CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        icon TEXT,
        required_count INTEGER
    )''')
    
    # Таблица полученных достижений
    c.execute('''CREATE TABLE IF NOT EXISTS user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        achievement_id INTEGER,
        earned_at TIMESTAMP,
        UNIQUE(user_id, achievement_id)
    )''')
    
    # Таблица стикеров
    c.execute('''CREATE TABLE IF NOT EXISTS stickers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        image_url TEXT,
        category TEXT,
        is_premium INTEGER DEFAULT 0
    )''')
    
    # Таблица избранных сообщений
    c.execute('''CREATE TABLE IF NOT EXISTS favorite_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message_id INTEGER,
        created_at TIMESTAMP,
        UNIQUE(user_id, message_id)
    )''')
    
    # Таблица уведомлений (для упоминаний)
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        source_id INTEGER,
        source_author TEXT,
        content TEXT,
        created_at TIMESTAMP,
        is_read INTEGER DEFAULT 0
    )''')
    
    # Таблица сторис
    c.execute('''CREATE TABLE IF NOT EXISTS stories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        media_path TEXT,
        media_type TEXT,
        text TEXT,
        created_at TIMESTAMP,
        expires_at TIMESTAMP,
        views INTEGER DEFAULT 0,
        reactions TEXT DEFAULT '{}',
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Таблица просмотров сторис
    c.execute('''CREATE TABLE IF NOT EXISTS story_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        story_id INTEGER,
        user_id INTEGER,
        viewed_at TIMESTAMP,
        UNIQUE(story_id, user_id)
    )''')
    
    # Таблица реакций на сторис
    c.execute('''CREATE TABLE IF NOT EXISTS story_reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        story_id INTEGER,
        user_id INTEGER,
        reaction TEXT,
        created_at TIMESTAMP,
        UNIQUE(story_id, user_id)
    )''')
    
    # Добавляем стандартные достижения
    achievements = [
        ('Первый пост', 'Опубликуйте свой первый пост', '📝', 1),
        ('Первый лайк', 'Получите первый лайк на свой пост', '❤️', 1),
        ('100 подписчиков', 'Соберите 100 подписчиков', '👥', 100),
        ('Мастер чата', 'Отправьте 1000 сообщений', '💬', 1000),
        ('Эксперт', 'Достигните 10 уровня', '⭐', 10),
    ]
    for a in achievements:
        c.execute("INSERT OR IGNORE INTO achievements (name, description, icon, required_count) VALUES (?, ?, ?, ?)", a)
    
    # Создаем админа
    admin_pass = hashlib.sha256("fastyk26tyr".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password, full_name, is_admin, is_verified, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("taranka", admin_pass, "Admin Taranka", 1, 1, datetime.now(), datetime.now()))
    
    conn.commit()
    conn.close()
    print("[DATABASE] База данных инициализирована")

init_db()

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn