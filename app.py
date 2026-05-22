import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_from_directory
import hashlib
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta
import threading
import time
import requests
import json
import secrets

# Для QR и WebSocket
from flask_sock import Sock

# Для 2FA
import pyotp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'users.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')

app = Flask(__name__)
app.secret_key = 'connect-secret-key-2026-render'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

sock = Sock(app)

# Создаем папки
os.makedirs(os.path.join(UPLOAD_FOLDER, 'photos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'gifs'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'voice'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'avatars'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'banners'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'stickers'), exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'ogg', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ========== Хранилища ==========
qr_sessions = {}
ws_connections = {}
verification_codes = {}
reset_tokens = {}

# ========== KEEP-ALIVE ФУНКЦИЯ ==========
def keep_alive():
    url = 'https://connectss-mapb.onrender.com'
    while True:
        try:
            print(f"[KEEP-ALIVE] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Сервер активен")
            requests.get(url, timeout=10)
        except Exception as e:
            print(f"[KEEP-ALIVE] Ошибка: {e}")
        time.sleep(60)

def start_keep_alive():
    thread = threading.Thread(target=keep_alive, daemon=True)
    thread.start()

# ========== ФИЛЬТРЫ ==========
@app.template_filter('format_time')
def format_time_filter(date_value):
    if not date_value:
        return ""
    if isinstance(date_value, datetime):
        return date_value.strftime('%d.%m.%Y %H:%M')
    if isinstance(date_value, str):
        try:
            date_obj = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S.%f')
            return date_obj.strftime('%d.%m.%Y %H:%M')
        except:
            try:
                date_obj = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S')
                return date_obj.strftime('%d.%m.%Y %H:%M')
            except:
                return date_value[:16]
    return str(date_value)[:16]

@app.template_filter('format_date')
def format_date_filter(date_value):
    if not date_value:
        return "январь 2026 г."
    if isinstance(date_value, datetime):
        months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        return f"{months[date_value.month - 1]} {date_value.year} г."
    if isinstance(date_value, str):
        try:
            date_obj = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S.%f')
            months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                      'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
            return f"{months[date_obj.month - 1]} {date_obj.year} г."
        except:
            return "январь 2026 г."
    return "январь 2026 г."

# ========== ИНИЦИАЛИЗАЦИЯ БД ==========
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not c.fetchone():
        c.execute('''CREATE TABLE users (
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
            last_seen TIMESTAMP,
            created_at TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            media_path TEXT,
            media_type TEXT,
            likes INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_id INTEGER,
            content TEXT,
            created_at TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE post_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_id INTEGER,
            UNIQUE(post_id, user_id)
        )''')
        
        c.execute('''CREATE TABLE followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER,
            following_id INTEGER,
            created_at TIMESTAMP,
            UNIQUE(follower_id, following_id)
        )''')
        
        c.execute('''CREATE TABLE chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER,
            user2_id INTEGER,
            is_group INTEGER DEFAULT 0,
            group_name TEXT,
            group_avatar TEXT,
            created_at TIMESTAMP,
            UNIQUE(user1_id, user2_id)
        )''')
        
        c.execute('''CREATE TABLE group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            joined_at TIMESTAMP,
            FOREIGN KEY(chat_id) REFERENCES chats(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        
        c.execute('''CREATE TABLE messages (
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
            FOREIGN KEY(chat_id) REFERENCES chats(id),
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )''')
        
        c.execute('''CREATE TABLE message_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            user_id INTEGER,
            reaction TEXT,
            created_at TIMESTAMP,
            UNIQUE(message_id, user_id)
        )''')
        
        c.execute('''CREATE TABLE blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blocker_id INTEGER,
            blocked_id INTEGER,
            created_at TIMESTAMP,
            UNIQUE(blocker_id, blocked_id)
        )''')
        
        c.execute('''CREATE TABLE reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            reported_id INTEGER,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            icon TEXT,
            required_count INTEGER
        )''')
        
        c.execute('''CREATE TABLE user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            achievement_id INTEGER,
            earned_at TIMESTAMP,
            UNIQUE(user_id, achievement_id)
        )''')
        
        c.execute('''CREATE TABLE stickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            image_url TEXT,
            category TEXT,
            is_premium INTEGER DEFAULT 0
        )''')
        
        c.execute('''CREATE TABLE favorite_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_id INTEGER,
            created_at TIMESTAMP,
            UNIQUE(user_id, message_id)
        )''')
        
        # Вставляем стандартные достижения
        achievements = [
            ('Первый пост', 'Опубликуйте свой первый пост', '📝', 1),
            ('Первый лайк', 'Получите первый лайк на свой пост', '❤️', 1),
            ('100 подписчиков', 'Соберите 100 подписчиков', '👥', 100),
            ('Мастер чата', 'Отправьте 1000 сообщений', '💬', 1000),
            ('Эксперт', 'Достигните 10 уровня', '⭐', 10),
        ]
        for a in achievements:
            c.execute("INSERT INTO achievements (name, description, icon, required_count) VALUES (?, ?, ?, ?)", a)
        
        # Создаем админа
        admin_pass = hash_password("fastyk26tyr")
        c.execute('''INSERT INTO users (username, password, full_name, is_admin, is_verified, created_at, last_seen) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  ("taranka", admin_pass, "Admin Taranka", 1, 1, datetime.now(), datetime.now()))
        
        conn.commit()
    
    conn.close()
    print("[DATABASE] База данных инициализирована")

init_db()

# ========== ФУНКЦИИ БД ==========
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def add_user(username, password, full_name, birthday, gender, bio, avatar, email=None, phone=None):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, full_name, birthday, gender, bio, avatar, email, phone, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (username, password, full_name or '', birthday or '', gender or '', bio or '', avatar or '', email or '', phone or '', datetime.now(), datetime.now()))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_user(username, password):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin, is_premium, is_verified, is_private, level FROM users WHERE username=? AND password=?", 
                  (username, password))
        user = c.fetchone()
        conn.close()
        return user
    except:
        return None

def get_user_by_id(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin, is_premium, is_verified, is_private, level, experience, email, phone, twofa_secret, created_at, last_seen FROM users WHERE id=?", (user_id,))
        user = c.fetchone()
        conn.close()
        return dict(user) if user else None
    except:
        return None

def get_user_by_email(email):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, email FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        return dict(user) if user else None
    except:
        return None

def update_last_seen(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET last_seen = ? WHERE id = ?", (datetime.now(), user_id))
        conn.commit()
        conn.close()
    except:
        pass

def update_user_profile(user_id, full_name=None, bio=None, birthday=None, gender=None, avatar=None, banner=None, email=None, phone=None):
    try:
        conn = get_db()
        c = conn.cursor()
        if full_name:
            c.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, user_id))
        if bio:
            c.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, user_id))
        if birthday:
            c.execute("UPDATE users SET birthday = ? WHERE id = ?", (birthday, user_id))
        if gender:
            c.execute("UPDATE users SET gender = ? WHERE id = ?", (gender, user_id))
        if avatar:
            c.execute("UPDATE users SET avatar = ? WHERE id = ?", (avatar, user_id))
        if banner:
            c.execute("UPDATE users SET banner = ? WHERE id = ?", (banner, user_id))
        if email:
            c.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
        if phone:
            c.execute("UPDATE users SET phone = ? WHERE id = ?", (phone, user_id))
        conn.commit()
        conn.close()
    except:
        pass

def add_post(user_id, content, media_path=None, media_type=None):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO posts (user_id, content, media_path, media_type, created_at) VALUES (?, ?, ?, ?, ?)",
                  (user_id, content or '', media_path, media_type, datetime.now()))
        post_id = c.lastrowid
        conn.commit()
        conn.close()
        return post_id
    except:
        return None

def get_all_posts():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''SELECT posts.*, users.username, users.avatar, users.full_name, users.is_admin, users.is_premium, users.is_verified, users.level
                     FROM posts 
                     JOIN users ON posts.user_id = users.id 
                     ORDER BY posts.created_at DESC''')
        posts = c.fetchall()
        conn.close()
        return [dict(post) for post in posts]
    except:
        return []

def get_user_posts(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''SELECT posts.*, users.username, users.avatar, users.full_name, users.is_admin, users.is_premium, users.is_verified, users.level
                     FROM posts 
                     JOIN users ON posts.user_id = users.id 
                     WHERE posts.user_id = ?
                     ORDER BY posts.created_at DESC''', (user_id,))
        posts = c.fetchall()
        conn.close()
        return [dict(post) for post in posts]
    except:
        return []

def add_comment(post_id, user_id, content):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO comments (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
                  (post_id, user_id, content, datetime.now()))
        conn.commit()
        conn.close()
    except:
        pass

def get_comments(post_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''SELECT comments.*, users.username, users.avatar, users.is_admin, users.is_premium, users.is_verified
                     FROM comments 
                     JOIN users ON comments.user_id = users.id 
                     WHERE comments.post_id = ? 
                     ORDER BY comments.created_at ASC''', (post_id,))
        comments = c.fetchall()
        conn.close()
        return [dict(comment) for comment in comments]
    except:
        return []

def like_post(post_id, user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)", (post_id, user_id))
        c.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def has_liked_post(post_id, user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
        result = c.fetchone()
        conn.close()
        return result is not None
    except:
        return False

def unlike_post(post_id, user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
        c.execute("UPDATE posts SET likes = likes - 1 WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()
    except:
        pass

def follow_user(follower_id, following_id):
    if follower_id == following_id:
        return False
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO followers (follower_id, following_id, created_at) VALUES (?, ?, ?)",
                  (follower_id, following_id, datetime.now()))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def unfollow_user(follower_id, following_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM followers WHERE follower_id = ? AND following_id = ?", 
                  (follower_id, following_id))
        conn.commit()
        conn.close()
    except:
        pass

def is_following(follower_id, following_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM followers WHERE follower_id = ? AND following_id = ?", 
                  (follower_id, following_id))
        result = c.fetchone()
        conn.close()
        return result is not None
    except:
        return False

def get_followers_count(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM followers WHERE following_id = ?", (user_id,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def get_following_count(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM followers WHERE follower_id = ?", (user_id,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def search_users(query):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, full_name, bio, avatar, is_admin, is_premium, is_verified, level FROM users WHERE username LIKE ? OR full_name LIKE ? LIMIT 20", 
                  (f'%{query}%', f'%{query}%'))
        users = c.fetchall()
        conn.close()
        return [dict(user) for user in users]
    except:
        return []

def delete_post(post_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_all_users():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, full_name, is_admin, is_premium, is_verified, level, created_at, last_seen FROM users ORDER BY created_at DESC")
        users = c.fetchall()
        conn.close()
        return [dict(user) for user in users]
    except:
        return []

def get_total_users():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def get_today_registrations():
    try:
        conn = get_db()
        c = conn.cursor()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        c.execute("SELECT COUNT(*) FROM users WHERE created_at > ?", (today,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def get_online_users():
    try:
        conn = get_db()
        c = conn.cursor()
        five_min_ago = datetime.now() - timedelta(minutes=5)
        c.execute("SELECT COUNT(*) FROM users WHERE last_seen > ?", (five_min_ago,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def get_total_posts():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM posts")
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def make_admin(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def remove_admin(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET is_admin = 0 WHERE id = ? AND username != 'taranka'", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def make_premium(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET is_premium = 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def verify_user(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

# ========== ФУНКЦИИ ДЛЯ ЧАТОВ ==========
def get_or_create_chat(user1_id, user2_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM chats WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)",
              (user1_id, user2_id, user2_id, user1_id))
    chat = c.fetchone()
    if chat:
        conn.close()
        return chat[0]
    c.execute("INSERT INTO chats (user1_id, user2_id, created_at) VALUES (?, ?, ?)",
              (user1_id, user2_id, datetime.now()))
    chat_id = c.lastrowid
    conn.commit()
    conn.close()
    return chat_id

def send_message(sender_id, receiver_id, message, reply_to=None, media_path=None):
    chat_id = get_or_create_chat(sender_id, receiver_id)
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (chat_id, sender_id, receiver_id, message, media_path, reply_to, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (chat_id, sender_id, receiver_id, message, media_path, reply_to or 0, datetime.now()))
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Добавляем опыт за сообщение
    add_experience(sender_id, 1)
    return msg_id

def get_messages(user_id, other_user_id, limit=50):
    chat_id = get_or_create_chat(user_id, other_user_id)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT messages.*, users.username, users.avatar, users.is_premium, users.is_verified
                 FROM messages 
                 JOIN users ON messages.sender_id = users.id 
                 WHERE chat_id = ? AND messages.is_deleted = 0
                 ORDER BY messages.created_at ASC LIMIT ?''', (chat_id, limit))
    messages = c.fetchall()
    
    result = []
    for msg in messages:
        msg_dict = dict(msg)
        # Получаем реакции для сообщения
        c2 = conn.cursor()
        c2.execute("SELECT reaction, COUNT(*) FROM message_reactions WHERE message_id = ? GROUP BY reaction", (msg_dict['id'],))
        reactions = {r[0]: r[1] for r in c2.fetchall()}
        msg_dict['reactions'] = reactions
        result.append(msg_dict)
    conn.close()
    return result

def get_unread_count(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def mark_messages_read(chat_id, user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("UPDATE messages SET is_read = 1 WHERE chat_id = ? AND receiver_id = ?", (chat_id, user_id))
    conn.commit()
    conn.close()

def get_user_chats(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT DISTINCT 
                    chats.id as chat_id,
                    CASE 
                        WHEN chats.user1_id = ? THEN chats.user2_id
                        ELSE chats.user1_id
                    END as other_user_id,
                    users.username,
                    users.avatar,
                    users.is_premium,
                    users.is_verified,
                    users.level,
                    (SELECT message FROM messages WHERE chat_id = chats.id AND is_deleted = 0 ORDER BY created_at DESC LIMIT 1) as last_message,
                    (SELECT created_at FROM messages WHERE chat_id = chats.id AND is_deleted = 0 ORDER BY created_at DESC LIMIT 1) as last_message_time,
                    (SELECT COUNT(*) FROM messages WHERE chat_id = chats.id AND receiver_id = ? AND is_read = 0) as unread_count
                 FROM chats
                 JOIN users ON (CASE 
                        WHEN chats.user1_id = ? THEN chats.user2_id
                        ELSE chats.user1_id
                    END) = users.id
                 WHERE chats.user1_id = ? OR chats.user2_id = ?
                 ORDER BY last_message_time DESC''', (user_id, user_id, user_id, user_id, user_id))
    chats = c.fetchall()
    conn.close()
    return [dict(chat) for chat in chats]

# ========== ФУНКЦИИ ДЛЯ РЕЙТИНГА И УРОВНЕЙ ==========
def add_experience(user_id, exp):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT experience, level FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if user:
            new_exp = user[0] + exp
            new_level = user[1]
            exp_needed = new_level * 100
            while new_exp >= exp_needed:
                new_exp -= exp_needed
                new_level += 1
                exp_needed = new_level * 100
            c.execute("UPDATE users SET experience = ?, level = ? WHERE id = ?", (new_exp, new_level, user_id))
            conn.commit()
            check_achievements(user_id)
    except:
        pass
    finally:
        conn.close()

def get_user_level(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT level, experience FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        return {'level': user[0], 'experience': user[1]} if user else {'level': 1, 'experience': 0}
    except:
        return {'level': 1, 'experience': 0}

# ========== ФУНКЦИИ ДЛЯ БЛОКИРОВКИ ==========
def block_user(blocker_id, blocked_id):
    if blocker_id == blocked_id:
        return False
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO blocks (blocker_id, blocked_id, created_at) VALUES (?, ?, ?)",
                  (blocker_id, blocked_id, datetime.now()))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def unblock_user(blocker_id, blocked_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
        conn.commit()
    except:
        pass
    finally:
        conn.close()

def is_blocked(user_id, other_user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM blocks WHERE blocker_id = ? AND blocked_id = ?", (user_id, other_user_id))
        result = c.fetchone()
        conn.close()
        return result is not None
    except:
        return False

# ========== ФУНКЦИИ ДЛЯ ЖАЛОБ ==========
def report_user(reporter_id, reported_id, reason):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO reports (reporter_id, reported_id, reason, created_at) VALUES (?, ?, ?, ?)",
                  (reporter_id, reported_id, reason, datetime.now()))
        conn.commit()
    except:
        pass
    finally:
        conn.close()

# ========== ФУНКЦИИ ДЛЯ ДОСТИЖЕНИЙ ==========
def check_achievements(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ?", (user_id,))
        posts_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM followers WHERE following_id = ?", (user_id,))
        followers_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM messages WHERE sender_id = ?", (user_id,))
        messages_count = c.fetchone()[0]
        
        c.execute("SELECT level FROM users WHERE id = ?", (user_id,))
        level = c.fetchone()[0]
        
        achievements_to_check = {
            'Первый пост': posts_count >= 1,
            '100 подписчиков': followers_count >= 100,
            'Мастер чата': messages_count >= 1000,
            'Эксперт': level >= 10,
        }
        
        new_achievements = []
        for name, condition in achievements_to_check.items():
            if condition:
                c.execute("SELECT id FROM achievements WHERE name = ?", (name,))
                ach = c.fetchone()
                if ach:
                    c.execute("SELECT id FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (user_id, ach[0]))
                    if not c.fetchone():
                        c.execute("INSERT INTO user_achievements (user_id, achievement_id, earned_at) VALUES (?, ?, ?)",
                                  (user_id, ach[0], datetime.now()))
                        new_achievements.append(name)
        
        conn.commit()
        return new_achievements
    except:
        return []
    finally:
        conn.close()

def get_user_achievements(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''SELECT achievements.*, user_achievements.earned_at
                     FROM achievements
                     JOIN user_achievements ON achievements.id = user_achievements.achievement_id
                     WHERE user_achievements.user_id = ?''', (user_id,))
        achievements = c.fetchall()
        conn.close()
        return [dict(ach) for ach in achievements]
    except:
        return []

# ========== ФУНКЦИИ ДЛЯ РЕАКЦИЙ ==========
def add_reaction(message_id, user_id, reaction):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO message_reactions (message_id, user_id, reaction, created_at) VALUES (?, ?, ?, ?)",
                  (message_id, user_id, reaction, datetime.now()))
        conn.commit()
        return True
    except:
        c.execute("UPDATE message_reactions SET reaction = ? WHERE message_id = ? AND user_id = ?",
                  (reaction, message_id, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def get_reactions(message_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT reaction, COUNT(*) FROM message_reactions WHERE message_id = ? GROUP BY reaction", (message_id,))
        reactions = c.fetchall()
        conn.close()
        return {r[0]: r[1] for r in reactions}
    except:
        return {}

# ========== ФУНКЦИИ ДЛЯ ИЗБРАННЫХ СООБЩЕНИЙ ==========
def favorite_message(user_id, message_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO favorite_messages (user_id, message_id, created_at) VALUES (?, ?, ?)",
                  (user_id, message_id, datetime.now()))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def unfavorite_message(user_id, message_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM favorite_messages WHERE user_id = ? AND message_id = ?", (user_id, message_id))
        conn.commit()
    except:
        pass
    finally:
        conn.close()

# ========== ФУНКЦИИ ДЛЯ ПОИСКА ПО ЧАТУ ==========
def search_messages(chat_id, query, user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM messages WHERE chat_id = ? AND message LIKE ? AND is_deleted = 0 ORDER BY created_at DESC LIMIT 50",
                  (chat_id, f'%{query}%'))
        messages = c.fetchall()
        conn.close()
        return [dict(msg) for msg in messages]
    except:
        return []

# ========== ДЕКОРАТОРЫ ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        update_last_seen(session['user_id'])
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = get_user_by_id(session['user_id'])
        if not user or not user.get('is_admin'):
            return "Access denied", 403
        return f(*args, **kwargs)
    return decorated_function

# ========== МАРШРУТЫ ==========
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('feed'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])
        full_name = request.form.get('full_name', '')
        birthday = request.form.get('birthday', '')
        gender = request.form.get('gender', '')
        bio = request.form.get('bio', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        
        avatar_path = None
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().timestamp()}_{username}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', filename)
                file.save(filepath)
                avatar_path = f'/static/uploads/avatars/{filename}'
        
        if add_user(username, password, full_name, birthday, gender, bio, avatar_path, email, phone):
            return redirect(url_for('login'))
        else:
            return render_template('register.html', error='Имя пользователя уже существует')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])
        
        user = get_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            session['is_premium'] = user['is_premium'] if len(user) > 9 else 0
            update_last_seen(user['id'])
            
            # Проверка 2FA
            user_data = get_user_by_id(user['id'])
            if user_data and user_data.get('twofa_secret'):
                return redirect(url_for('twofa_verify'))
            
            return redirect(url_for('feed'))
        else:
            return render_template('login.html', error='Неверное имя пользователя или пароль')
    return render_template('login.html')

# ========== QR ВХОД ==========
@sock.route('/ws/qr/<session_id>')
def ws_qr(ws, session_id):
    ws_connections[session_id] = ws
    try:
        while True:
            data = ws.receive()
            if data:
                pass
    except:
        pass
    finally:
        if session_id in ws_connections:
            del ws_connections[session_id]

@app.route('/qr-login')
def qr_login():
    session_id = secrets.token_urlsafe(32)
    qr_sessions[session_id] = {'status': 'pending', 'created_at': datetime.now()}
    return render_template('qr_login.html', session_id=session_id)

@app.route('/qr/scan/<session_id>')
def qr_scan(session_id):
    if session_id not in qr_sessions:
        qr_sessions[session_id] = {'status': 'pending', 'created_at': datetime.now()}
    return render_template('qr_scan.html', session_id=session_id)

@app.route('/api/qr/status/<session_id>')
def api_qr_status(session_id):
    if session_id in qr_sessions:
        return jsonify({'status': qr_sessions[session_id].get('status', 'pending')})
    return jsonify({'status': 'pending'})

@app.route('/api/qr/confirm', methods=['POST'])
@login_required
def api_qr_confirm():
    data = request.get_json()
    session_id = data.get('session_id')
    
    if session_id in qr_sessions:
        qr_sessions[session_id]['status'] = 'confirmed'
        qr_sessions[session_id]['user_id'] = session['user_id']
        
        # Отправляем через WebSocket
        if session_id in ws_connections:
            try:
                ws_connections[session_id].send(json.dumps({
                    'type': 'login_success',
                    'user_id': session['user_id'],
                    'username': session['username']
                }))
            except:
                pass
        
        return jsonify({'success': True, 'user_id': session['user_id'], 'username': session['username']})
    
    return jsonify({'success': False})

@app.route('/api/qr/login/<session_id>')
def api_qr_login(session_id):
    if session_id in qr_sessions and qr_sessions[session_id].get('status') == 'confirmed':
        user_id = qr_sessions[session_id].get('user_id')
        user = get_user_by_id(user_id)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            session['is_premium'] = user['is_premium']
            update_last_seen(user['id'])
            # Перенаправляем сразу на feed
            return redirect(url_for('feed'))
    
    return redirect(url_for('login'))

# ========== 2FA ==========
@app.route('/2fa/setup', methods=['POST'])
@login_required
def setup_2fa():
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(session['username'], issuer_name="Connect")
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET twofa_secret = ? WHERE id = ?", (secret, session['user_id']))
    conn.commit()
    conn.close()
    
    return jsonify({'secret': secret, 'uri': provisioning_uri})

@app.route('/2fa/verify', methods=['GET', 'POST'])
def twofa_verify():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        code = request.form.get('code')
        user = get_user_by_id(session['user_id'])
        
        if user and user.get('twofa_secret'):
            totp = pyotp.TOTP(user['twofa_secret'])
            if totp.verify(code):
                session['2fa_verified'] = True
                return redirect(url_for('feed'))
        
        return render_template('twofa.html', error='Неверный код')
    
    return render_template('twofa.html')

@app.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET twofa_secret = NULL WHERE id = ?", (session['user_id'],))
    conn.commit()
    conn.close()
    session.pop('2fa_verified', None)
    return jsonify({'success': True})

# ========== ВОССТАНОВЛЕНИЕ ПАРОЛЯ ==========
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = get_user_by_email(email)
        if user:
            token = secrets.token_urlsafe(32)
            reset_tokens[token] = {'user_id': user['id'], 'expires': datetime.now() + timedelta(hours=1)}
            reset_url = url_for('reset_password', token=token, _external=True)
            print(f"Ссылка для сброса пароля: {reset_url}")
            return render_template('forgot_password.html', message='Инструкция отправлена на email')
        return render_template('forgot_password.html', error='Email не найден')
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if token not in reset_tokens or reset_tokens[token]['expires'] < datetime.now():
        return "Ссылка недействительна или истекла", 400
    
    if request.method == 'POST':
        new_password = request.form.get('password')
        hashed_password = hash_password(new_password)
        user_id = reset_tokens[token]['user_id']
        
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))
        conn.commit()
        conn.close()
        
        del reset_tokens[token]
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

# ========== ПОДТВЕРЖДЕНИЕ EMAIL/ТЕЛЕФОНА ==========
@app.route('/verify/send', methods=['POST'])
@login_required
def send_verification():
    data = request.get_json()
    contact_type = data.get('type')
    contact = data.get('contact')
    
    if not contact:
        return jsonify({'success': False, 'error': 'Контакт не указан'})
    
    code = str(secrets.randbelow(900000) + 100000)
    verification_codes[session['user_id']] = {
        'code': code,
        'contact': contact,
        'type': contact_type,
        'expires': datetime.now() + timedelta(minutes=10)
    }
    
    print(f"Код подтверждения для {contact}: {code}")
    return jsonify({'success': True, 'message': 'Код отправлен'})

@app.route('/verify/confirm', methods=['POST'])
@login_required
def confirm_verification():
    data = request.get_json()
    code = data.get('code')
    
    if session['user_id'] in verification_codes:
        vc = verification_codes[session['user_id']]
        if vc['code'] == code and vc['expires'] > datetime.now():
            conn = get_db()
            c = conn.cursor()
            if vc['type'] == 'email':
                c.execute("UPDATE users SET email = ?, is_verified = 1 WHERE id = ?", (vc['contact'], session['user_id']))
            else:
                c.execute("UPDATE users SET phone = ?, is_verified = 1 WHERE id = ?", (vc['contact'], session['user_id']))
            conn.commit()
            conn.close()
            del verification_codes[session['user_id']]
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Неверный код'})

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========
@app.route('/feed', methods=['GET', 'POST'])
@login_required
def feed():
    if request.method == 'POST':
        content = request.form['content']
        media_path = None
        media_type = None
        
        if 'media' in request.files:
            file = request.files['media']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                ext = filename.rsplit('.', 1)[1].lower()
                
                if ext in ['mp3', 'wav', 'ogg', 'webm']:
                    subfolder = 'voice'
                    media_type = 'audio'
                elif ext == 'gif':
                    subfolder = 'gifs'
                    media_type = 'gif'
                else:
                    subfolder = 'photos'
                    media_type = 'image'
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
                file.save(filepath)
                media_path = f'/static/uploads/{subfolder}/{filename}'
        
        if content.strip() or media_path:
            add_post(session['user_id'], content, media_path, media_type)
            add_experience(session['user_id'], 5)
        return redirect(url_for('feed'))
    
    posts = get_all_posts()
    liked_posts = [post['id'] for post in posts if has_liked_post(post['id'], session['user_id'])]
    user = get_user_by_id(session['user_id'])
    
    return render_template('feed.html', 
                         username=session['username'], 
                         posts=posts, 
                         liked_posts=liked_posts,
                         user_id=session['user_id'],
                         is_admin=session.get('is_admin', False),
                         is_premium=session.get('is_premium', False),
                         user_avatar=user['avatar'] if user else None,
                         unread_count=get_unread_count(session['user_id']))

@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return "User not found", 404
    
    # Проверка блокировки
    if is_blocked(session['user_id'], user_id):
        return render_template('blocked.html', user=user)
    
    posts = get_user_posts(user_id)
    followers_count = get_followers_count(user_id)
    following_count = get_following_count(user_id)
    is_following_user = is_following(session['user_id'], user_id) if session['user_id'] != user_id else False
    current_user = get_user_by_id(session['user_id'])
    achievements = get_user_achievements(user_id)
    level_info = get_user_level(user_id)
    
    return render_template('profile.html', 
                         profile_user=user,
                         posts=posts,
                         followers_count=followers_count,
                         following_count=following_count,
                         is_following=is_following_user,
                         current_user_id=session['user_id'],
                         is_admin=session.get('is_admin', False),
                         is_premium=session.get('is_premium', False),
                         user_avatar=current_user['avatar'] if current_user else None,
                         session=session,
                         unread_count=get_unread_count(session['user_id']),
                         achievements=achievements,
                         level=level_info['level'],
                         experience=level_info['experience'])

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    full_name = request.form.get('full_name')
    bio = request.form.get('bio')
    birthday = request.form.get('birthday')
    gender = request.form.get('gender')
    email = request.form.get('email')
    phone = request.form.get('phone')
    avatar_path = None
    banner_path = None
    
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"avatar_{session['user_id']}_{datetime.now().timestamp()}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', filename)
            file.save(filepath)
            avatar_path = f'/static/uploads/avatars/{filename}'
    
    if 'banner' in request.files:
        file = request.files['banner']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"banner_{session['user_id']}_{datetime.now().timestamp()}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'banners', filename)
            file.save(filepath)
            banner_path = f'/static/uploads/banners/{filename}'
    
    update_user_profile(session['user_id'], full_name, bio, birthday, gender, avatar_path, banner_path, email, phone)
    return redirect(url_for('profile', user_id=session['user_id']))

@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow(user_id):
    if follow_user(session['user_id'], user_id):
        return jsonify({'success': True, 'following': True})
    return jsonify({'success': False, 'following': False})

@app.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow(user_id):
    unfollow_user(session['user_id'], user_id)
    return jsonify({'success': True, 'following': False})

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    users = search_users(query) if query else []
    return render_template('search.html', users=users, query=query, session=session)

@app.route('/post/<int:post_id>')
@login_required
def post_detail(post_id):
    posts = get_all_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post:
        return "Post not found", 404
    
    comments = get_comments(post_id)
    return render_template('post_detail.html', post=post, comments=comments, username=session['username'], user_id=session['user_id'])

@app.route('/add_comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment_route(post_id):
    content = request.form.get('content', '')
    if content.strip():
        add_comment(post_id, session['user_id'], content)
        add_experience(session['user_id'], 2)
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/like_post/<int:post_id>', methods=['POST'])
@login_required
def like_post_route(post_id):
    if has_liked_post(post_id, session['user_id']):
        unlike_post(post_id, session['user_id'])
        return jsonify({'liked': False, 'likes_count': 0})
    else:
        like_post(post_id, session['user_id'])
        posts = get_all_posts()
        post = next((p for p in posts if p['id'] == post_id), None)
        add_experience(session['user_id'], 1)
        return jsonify({'liked': True, 'likes_count': post['likes'] if post else 0})

@app.route('/admin')
@admin_required
def admin_panel():
    total_users = get_total_users()
    today_users = get_today_registrations()
    online_users = get_online_users()
    total_posts = get_total_posts()
    all_users = get_all_users()
    posts = get_all_posts()
    
    return render_template('admin.html', 
                         total_users=total_users,
                         today_users=today_users,
                         online_users=online_users,
                         total_posts=total_posts,
                         users=all_users,
                         posts=posts,
                         username=session['username'],
                         is_admin=True)

@app.route('/admin/delete_post/<int:post_id>', methods=['POST'])
@admin_required
def admin_delete_post(post_id):
    if delete_post(post_id):
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/admin/make_admin/<int:user_id>', methods=['POST'])
@admin_required
def admin_make_admin(user_id):
    user = get_user_by_id(user_id)
    if user and user['username'] != 'taranka':
        if make_admin(user_id):
            return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/admin/remove_admin/<int:user_id>', methods=['POST'])
@admin_required
def admin_remove_admin(user_id):
    user = get_user_by_id(user_id)
    if user and user['username'] != 'taranka':
        if remove_admin(user_id):
            return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/admin/reports')
@admin_required
def admin_reports():
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT reports.*, 
                 reporter.username as reporter_name, 
                 reported.username as reported_name
                 FROM reports 
                 JOIN users as reporter ON reports.reporter_id = reporter.id
                 JOIN users as reported ON reports.reported_id = reported.id
                 ORDER BY reports.created_at DESC''')
    reports = c.fetchall()
    conn.close()
    return render_template('admin_reports.html', reports=[dict(r) for r in reports])

@app.route('/admin/report/<int:report_id>/resolve', methods=['POST'])
@admin_required
def resolve_report(report_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE reports SET status = 'resolved' WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/buy_premium', methods=['POST'])
@login_required
def buy_premium():
    if make_premium(session['user_id']):
        session['is_premium'] = 1
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/chats')
@login_required
def chats():
    user_chats = get_user_chats(session['user_id'])
    unread_count = get_unread_count(session['user_id'])
    current_user = get_user_by_id(session['user_id'])
    return render_template('chats.html', 
                         chats=user_chats,
                         username=session['username'], 
                         unread_count=unread_count, 
                         user_id=session['user_id'], 
                         is_admin=session.get('is_admin', False), 
                         is_premium=session.get('is_premium', False),
                         user_avatar=current_user['avatar'] if current_user else None)

@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    other_user = get_user_by_id(user_id)
    if not other_user:
        return "User not found", 404
    
    if is_blocked(session['user_id'], user_id) or is_blocked(user_id, session['user_id']):
        return render_template('blocked.html', user=other_user)
    
    messages = get_messages(session['user_id'], user_id)
    current_user = get_user_by_id(session['user_id'])
    chat_id = get_or_create_chat(session['user_id'], user_id)
    mark_messages_read(chat_id, session['user_id'])
    
    level_info = get_user_level(session['user_id'])
    
    return render_template('chat.html', 
                         other_user=other_user, 
                         messages=messages, 
                         username=session['username'], 
                         user_id=session['user_id'],
                         user_avatar=current_user['avatar'] if current_user else None,
                         level=level_info['level'])

@app.route('/send_message', methods=['POST'])
@login_required
def send_message_route():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    message = data.get('message', '')
    reply_to = data.get('reply_to', None)
    
    if message.strip():
        send_message(session['user_id'], receiver_id, message, reply_to)
        add_experience(session['user_id'], 1)
    return jsonify({'success': True})

@app.route('/send_file', methods=['POST'])
@login_required
def send_file_route():
    receiver_id = request.form.get('receiver_id')
    file = request.files.get('file')
    
    if file:
        filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
        subfolder = 'photos' if file.content_type.startswith('image') else 'voice'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
        file.save(filepath)
        media_path = f'/static/uploads/{subfolder}/{filename}'
        send_message(session['user_id'], receiver_id, f"📎 Файл: {filename}", media_path=media_path)
    
    return jsonify({'success': True})

@app.route('/send_voice', methods=['POST'])
@login_required
def send_voice_route():
    receiver_id = request.form.get('receiver_id')
    voice = request.files.get('voice')
    
    if voice:
        filename = secure_filename(f"voice_{datetime.now().timestamp()}.webm")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'voice', filename)
        voice.save(filepath)
        media_path = f'/static/uploads/voice/{filename}'
        send_message(session['user_id'], receiver_id, "🎤 Голосовое сообщение", media_path=media_path)
    
    return jsonify({'success': True})

@app.route('/api/messages/<int:user_id>')
@login_required
def api_messages(user_id):
    messages = get_messages(session['user_id'], user_id)
    result = []
    for msg in messages:
        result.append({
            'id': msg['id'],
            'sender_id': msg['sender_id'],
            'message': msg['message'],
            'created_at': msg['created_at'].strftime('%H:%M') if isinstance(msg['created_at'], datetime) else str(msg['created_at'])[:5],
            'is_read': msg['is_read'],
            'is_edited': msg['is_edited'],
            'reply_to': msg['reply_to'],
            'reactions': msg.get('reactions', {})
        })
    return jsonify(result)

@app.route('/api/unread_count')
@login_required
def api_unread_count():
    return jsonify({'count': get_unread_count(session['user_id'])})

@app.route('/api/online_status', methods=['POST'])
@login_required
def api_online_status():
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    statuses = {}
    for user_id in user_ids:
        user = get_user_by_id(user_id)
        if user and user.get('last_seen'):
            last_seen = user['last_seen']
            if isinstance(last_seen, str):
                try:
                    last_seen = datetime.strptime(last_seen, '%Y-%m-%d %H:%M:%S.%f')
                except:
                    last_seen = datetime.now() - timedelta(days=1)
            is_online = (datetime.now() - last_seen).seconds < 300
            statuses[user_id] = is_online
        else:
            statuses[user_id] = False
    return jsonify(statuses)

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'users': get_total_users(),
        'posts': get_total_posts()
    })

@app.route('/api/add_reaction', methods=['POST'])
@login_required
def api_add_reaction():
    data = request.get_json()
    message_id = data.get('message_id')
    reaction = data.get('reaction')
    add_reaction(message_id, session['user_id'], reaction)
    return jsonify({'success': True})

@app.route('/api/forward_message', methods=['POST'])
@login_required
def api_forward_message():
    data = request.get_json()
    message_id = data.get('message_id')
    to_user_id = data.get('to_user_id')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT message FROM messages WHERE id = ?", (message_id,))
    msg = c.fetchone()
    if msg:
        send_message(session['user_id'], to_user_id, f"📨 Переслано: {msg['message']}")
    conn.close()
    return jsonify({'success': True})

@app.route('/api/edit_message', methods=['POST'])
@login_required
def api_edit_message():
    data = request.get_json()
    message_id = data.get('message_id')
    new_message = data.get('message')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE messages SET message = ?, is_edited = 1 WHERE id = ? AND sender_id = ?", 
              (new_message, message_id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/delete_message', methods=['POST'])
@login_required
def api_delete_message():
    data = request.get_json()
    message_id = data.get('message_id')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE messages SET is_deleted = 1 WHERE id = ? AND (sender_id = ? OR receiver_id = ?)", 
              (message_id, session['user_id'], session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/favorite_message', methods=['POST'])
@login_required
def api_favorite_message():
    data = request.get_json()
    message_id = data.get('message_id')
    favorite_message(session['user_id'], message_id)
    return jsonify({'success': True})

@app.route('/api/search_messages/<int:user_id>')
@login_required
def api_search_messages(user_id):
    query = request.args.get('q', '')
    chat_id = get_or_create_chat(session['user_id'], user_id)
    messages = search_messages(chat_id, query, session['user_id'])
    return jsonify(messages)

@app.route('/api/block_user/<int:user_id>', methods=['POST'])
@login_required
def api_block_user(user_id):
    if block_user(session['user_id'], user_id):
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/unblock_user/<int:user_id>', methods=['POST'])
@login_required
def api_unblock_user(user_id):
    unblock_user(session['user_id'], user_id)
    return jsonify({'success': True})

@app.route('/api/report_user/<int:user_id>', methods=['POST'])
@login_required
def api_report_user(user_id):
    data = request.get_json()
    reason = data.get('reason', 'Нарушение правил')
    report_user(session['user_id'], user_id, reason)
    return jsonify({'success': True})

@app.route('/api/set_private', methods=['POST'])
@login_required
def api_set_private():
    data = request.get_json()
    is_private = data.get('is_private', 0)
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET is_private = ? WHERE id = ?", (is_private, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/get_achievements')
@login_required
def api_get_achievements():
    achievements = get_user_achievements(session['user_id'])
    return jsonify({'achievements': achievements})

@app.route('/api/get_level')
@login_required
def api_get_level():
    level_info = get_user_level(session['user_id'])
    return jsonify(level_info)

@app.route('/api/me')
@login_required
def api_me():
    user = get_user_by_id(session['user_id'])
    if user:
        return jsonify({'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'avatar': user['avatar']
        }})
    return jsonify({'user': None})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    start_keep_alive()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)