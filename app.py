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
import shutil
import re

# Для QR и WebSocket
from flask_sock import Sock

# Для 2FA
import pyotp

# Для бэкапов
from apscheduler.schedulers.background import BackgroundScheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'users.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')

app = Flask(__name__)
app.secret_key = 'connect-secret-key-2026-render'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

sock = Sock(app)

# Создаем папки
os.makedirs(os.path.join(UPLOAD_FOLDER, 'photos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'gifs'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'voice'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'avatars'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'banners'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'stickers'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'wallpapers'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'stories_photos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'stories_video'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'backups'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'playlists'), exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'ogg', 'webm', 'mp4', 'mov', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


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


# ========== ФУНКЦИИ БД ==========
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def update_last_seen(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET last_seen = ? WHERE id = ?", (datetime.now(), user_id))
        conn.commit()
        conn.close()
    except:
        pass

def get_user_by_id(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin, is_premium, is_verified, is_private, level, experience, email, phone, twofa_secret, theme_color, theme_background, chat_wallpaper, animations_enabled, created_at, last_seen FROM users WHERE id=?", (user_id,))
        user = c.fetchone()
        conn.close()
        return dict(user) if user else None
    except:
        return None

def get_user(username, password):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin, is_premium, is_verified, is_private, level, theme_color, theme_background, chat_wallpaper, animations_enabled FROM users WHERE username=? AND password=?", 
                  (username, password))
        user = c.fetchone()
        conn.close()
        return user
    except:
        return None

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

def update_user_profile(user_id, full_name=None, bio=None, birthday=None, gender=None, avatar=None, banner=None, email=None, phone=None):
    try:
        conn = get_db()
        c = conn.cursor()
        if full_name is not None:
            c.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, user_id))
        if bio is not None:
            c.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, user_id))
        if birthday is not None:
            c.execute("UPDATE users SET birthday = ? WHERE id = ?", (birthday, user_id))
        if gender is not None:
            c.execute("UPDATE users SET gender = ? WHERE id = ?", (gender, user_id))
        if avatar is not None:
            c.execute("UPDATE users SET avatar = ? WHERE id = ?", (avatar, user_id))
        if banner is not None:
            c.execute("UPDATE users SET banner = ? WHERE id = ?", (banner, user_id))
        if email is not None:
            c.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
        if phone is not None:
            c.execute("UPDATE users SET phone = ? WHERE id = ?", (phone, user_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

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
        return True
    except:
        return False

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


# ========== УПОМИНАНИЯ (@username) ==========
def extract_mentions(text):
    """Извлекает все упоминания @username из текста"""
    if not text:
        return []
    mentions = re.findall(r'@([a-zA-Z0-9_]+)', text)
    return list(set(mentions))

def send_mention_notification(mentioned_user_id, post_id, comment_id, author_name, content):
    """Отправляет уведомление пользователю об упоминании"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Создаём таблицу уведомлений если её нет
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
        
        c.execute('''
            INSERT INTO notifications (user_id, type, source_id, source_author, content, created_at, is_read)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (mentioned_user_id, 'mention', post_id or comment_id, author_name, content[:200], datetime.now()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Mention error: {e}")
        return False

@app.route('/api/mentions')
@login_required
def get_mentions():
    """Получить все упоминания пользователя"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM notifications 
            WHERE user_id = ? AND type = 'mention'
            ORDER BY created_at DESC
            LIMIT 50
        ''', (session['user_id'],))
        notifications = c.fetchall()
        conn.close()
        return jsonify([dict(n) for n in notifications])
    except:
        return jsonify([])

@app.route('/api/mentions/mark_read', methods=['POST'])
@login_required
def mark_mentions_read():
    """Отметить упоминания как прочитанные"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            UPDATE notifications SET is_read = 1 
            WHERE user_id = ? AND type = 'mention'
        ''', (session['user_id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})


# ========== СТОРИС ==========
def delete_expired_stories():
    """Удаляет истекшие сторис"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM stories WHERE expires_at < ?", (datetime.now(),))
        conn.commit()
        conn.close()
    except:
        pass

@app.route('/api/stories/upload', methods=['POST'])
@login_required
def upload_story():
    """Загрузка новой истории"""
    try:
        media_path = None
        media_type = None
        text = request.form.get('text', '')
        
        if 'media' not in request.files:
            return jsonify({'success': False, 'error': 'No media file'}), 400
        
        file = request.files['media']
        if not file or not file.filename:
            return jsonify({'success': False, 'error': 'Empty file'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed'}), 400
        
        filename = secure_filename(f"story_{session['user_id']}_{int(datetime.now().timestamp())}_{file.filename}")
        ext = filename.rsplit('.', 1)[1].lower()
        
        if ext in ['mp4', 'webm', 'mov', 'avi']:
            subfolder = 'stories_video'
            media_type = 'video'
        else:
            subfolder = 'stories_photos'
            media_type = 'photo'
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
        file.save(filepath)
        media_path = f'/static/uploads/{subfolder}/{filename}'
        
        expires_at = datetime.now() + timedelta(hours=24)
        
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO stories (user_id, media_path, media_type, text, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], media_path, media_type, text, datetime.now(), expires_at))
        story_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'story_id': story_id})
    except Exception as e:
        print(f"Upload story error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stories')
@login_required
def get_stories():
    """Получить активные истории"""
    try:
        # Удаляем истекшие
        delete_expired_stories()
        
        conn = get_db()
        c = conn.cursor()
        
        # Получаем подписки пользователя
        c.execute("SELECT following_id FROM followers WHERE follower_id = ?", (session['user_id'],))
        following = [row[0] for row in c.fetchall()]
        following.append(session['user_id'])
        
        if not following:
            following = [session['user_id']]
        
        placeholders = ','.join('?' * len(following))
        query = f'''
            SELECT s.*, u.username, u.avatar, u.full_name, u.is_premium, u.is_verified
            FROM stories s
            JOIN users u ON s.user_id = u.id
            WHERE s.user_id IN ({placeholders}) AND s.expires_at > ?
            ORDER BY s.created_at DESC
        '''
        c.execute(query, following + [datetime.now()])
        
        stories = c.fetchall()
        conn.close()
        
        # Группируем по пользователям
        stories_by_user = {}
        for story in stories:
            story_dict = dict(story)
            user_id = story_dict['user_id']
            if user_id not in stories_by_user:
                stories_by_user[user_id] = {
                    'user': {
                        'id': user_id,
                        'username': story_dict['username'],
                        'avatar': story_dict['avatar'],
                        'full_name': story_dict['full_name'],
                        'is_premium': story_dict['is_premium'],
                        'is_verified': story_dict['is_verified']
                    },
                    'stories': []
                }
            stories_by_user[user_id]['stories'].append(story_dict)
        
        return jsonify({'success': True, 'stories': list(stories_by_user.values())})
    except Exception as e:
        print(f"Get stories error: {e}")
        return jsonify({'success': True, 'stories': []})

@app.route('/api/stories/<int:story_id>/view', methods=['POST'])
@login_required
def view_story(story_id):
    """Отметить просмотр истории"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO story_views (story_id, user_id, viewed_at)
            VALUES (?, ?, ?)
        ''', (story_id, session['user_id'], datetime.now()))
        c.execute('UPDATE stories SET views = views + 1 WHERE id = ?', (story_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})

@app.route('/api/stories/<int:story_id>/react', methods=['POST'])
@login_required
def react_to_story(story_id):
    """Добавить реакцию на историю"""
    try:
        data = request.get_json()
        reaction = data.get('reaction', '❤️')
        
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO story_reactions (story_id, user_id, reaction, created_at)
            VALUES (?, ?, ?, ?)
        ''', (story_id, session['user_id'], reaction, datetime.now()))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})

@app.route('/stories')
@login_required
def stories_page():
    """Страница просмотра сторис"""
    return render_template('stories.html', 
                         username=session['username'],
                         user_id=session['user_id'],
                         is_admin=session.get('is_admin', False),
                         is_premium=session.get('is_premium', False))


# ========== ФОРМАТИРОВАНИЕ ==========
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
    return "январь 2026 г."


# ========== CONNECT MUSIC API ==========
def format_duration(seconds):
    if not seconds:
        return '0:00'
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

def get_demo_tracks():
    return [
        {'id': 1, 'title': 'Summer Vibes', 'artist': 'Connect Artists', 'duration': '3:30', 'cover': '', 'preview': 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3', 'link': ''},
        {'id': 2, 'title': 'Midnight Dreams', 'artist': 'Connect Stars', 'duration': '4:15', 'cover': '', 'preview': 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3', 'link': ''},
        {'id': 3, 'title': 'Electric Feel', 'artist': 'Connect Waves', 'duration': '3:45', 'cover': '', 'preview': 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3', 'link': ''}
    ]

def get_user_playlist_file(user_id):
    playlist_dir = os.path.join(BASE_DIR, 'playlists')
    os.makedirs(playlist_dir, exist_ok=True)
    return os.path.join(playlist_dir, f'user_{user_id}_playlist.json')

def get_user_playlist(user_id):
    playlist_file = get_user_playlist_file(user_id)
    if os.path.exists(playlist_file):
        try:
            with open(playlist_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_user_playlist(user_id, playlist):
    playlist_file = get_user_playlist_file(user_id)
    with open(playlist_file, 'w', encoding='utf-8') as f:
        json.dump(playlist, f, ensure_ascii=False, indent=2)

@app.route('/api/music/search')
@login_required
def music_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'No query'}), 400
    try:
        response = requests.get('https://api.deezer.com/search', params={'q': query, 'limit': 30}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            tracks = []
            for item in data.get('data', []):
                if item.get('preview'):
                    tracks.append({
                        'id': item.get('id'),
                        'title': item.get('title'),
                        'artist': item.get('artist', {}).get('name', 'Unknown'),
                        'duration': format_duration(item.get('duration', 0)),
                        'cover': item.get('album', {}).get('cover_medium', ''),
                        'preview': item.get('preview'),
                        'link': item.get('link', '')
                    })
            return jsonify({'success': True, 'tracks': tracks})
        return jsonify({'success': True, 'tracks': get_demo_tracks()})
    except:
        return jsonify({'success': True, 'tracks': get_demo_tracks()})

@app.route('/api/music/favorites')
@login_required
def music_favorites():
    playlist = get_user_playlist(session['user_id'])
    return jsonify({'success': True, 'tracks': playlist})

@app.route('/api/music/add_favorite', methods=['POST'])
@login_required
def music_add_favorite():
    data = request.get_json()
    track = data.get('track', {})
    if not track.get('id'):
        return jsonify({'success': False, 'error': 'No track data'}), 400
    
    playlist = get_user_playlist(session['user_id'])
    if not any(t.get('id') == track.get('id') for t in playlist):
        track['added_at'] = datetime.now().isoformat()
        playlist.insert(0, track)
        save_user_playlist(session['user_id'], playlist)
        return jsonify({'success': True, 'added': True})
    return jsonify({'success': True, 'added': False, 'message': 'Already in favorites'})

@app.route('/api/music/remove_favorite', methods=['POST'])
@login_required
def music_remove_favorite():
    data = request.get_json()
    track_id = data.get('track_id')
    if not track_id:
        return jsonify({'success': False, 'error': 'No track id'}), 400
    
    playlist = get_user_playlist(session['user_id'])
    playlist = [t for t in playlist if t.get('id') != track_id]
    save_user_playlist(session['user_id'], playlist)
    return jsonify({'success': True, 'removed': True})

@app.route('/api/music/playlist/<playlist_id>')
@login_required
def music_playlist(playlist_id):
    try:
        response = requests.get(f'https://api.deezer.com/playlist/{playlist_id}/tracks', params={'limit': 30}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            tracks = []
            for item in data.get('data', []):
                if item.get('preview'):
                    tracks.append({
                        'id': item.get('id'),
                        'title': item.get('title'),
                        'artist': item.get('artist', {}).get('name', 'Unknown'),
                        'duration': format_duration(item.get('duration', 0)),
                        'cover': item.get('album', {}).get('cover_medium', ''),
                        'preview': item.get('preview'),
                        'link': item.get('link', '')
                    })
            return jsonify({'success': True, 'tracks': tracks})
        return jsonify({'success': True, 'tracks': get_demo_tracks()})
    except:
        return jsonify({'success': True, 'tracks': get_demo_tracks()})


# ========== РЕЗЕРВНОЕ КОПИРОВАНИЕ ==========
def backup_database():
    backup_dir = os.path.join(BASE_DIR, 'backups')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'users_backup_{timestamp}.db')
    shutil.copy2(DATABASE_PATH, backup_path)
    print(f"✅ Бэкап создан: {backup_path}")
    
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('users_backup_')])
    while len(backups) > 10:
        os.remove(os.path.join(backup_dir, backups.pop(0)))

scheduler = BackgroundScheduler()
scheduler.add_job(func=backup_database, trigger="cron", hour=3, minute=0)
scheduler.start()


# ========== KEEP-ALIVE ==========
def keep_alive():
    url = 'https://connectss-mapb.onrender.com'
    while True:
        try:
            requests.get(url, timeout=10)
        except:
            pass
        time.sleep(60)

def start_keep_alive():
    thread = threading.Thread(target=keep_alive, daemon=True)
    thread.start()


# ========== ОСНОВНЫЕ МАРШРУТЫ ==========
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
            return redirect(url_for('feed'))
        return render_template('login.html', error='Неверное имя пользователя или пароль')
    return render_template('login.html')

@app.route('/feed', methods=['GET', 'POST'])
@login_required
def feed():
    if request.method == 'POST':
        content = request.form.get('content', '')
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
                elif ext in ['mp4', 'mov', 'avi', 'webm']:
                    subfolder = 'photos'
                    media_type = 'video'
                else:
                    subfolder = 'photos'
                    media_type = 'image'
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
                file.save(filepath)
                media_path = f'/static/uploads/{subfolder}/{filename}'
        
        if content.strip() or media_path:
            post_id = add_post(session['user_id'], content, media_path, media_type)
            
            # Обработка упоминаний
            mentions = extract_mentions(content)
            for mention in mentions:
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT id FROM users WHERE username = ?", (mention,))
                user = c.fetchone()
                conn.close()
                if user and user[0] != session['user_id']:
                    send_mention_notification(user[0], post_id, None, session['username'], content)
            
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
    
    update_user_profile(session['user_id'], full_name, bio, birthday, gender, avatar_path, banner_path)
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
        
        # Обработка упоминаний в комментарии
        mentions = extract_mentions(content)
        for mention in mentions:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE username = ?", (mention,))
            user = c.fetchone()
            conn.close()
            if user and user[0] != session['user_id']:
                send_mention_notification(user[0], None, post_id, session['username'], content)
        
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


# ========== АДМИН ПАНЕЛЬ ==========
@app.route('/admin')
@admin_required
def admin_panel():
    total_users = get_total_users()
    today_users = get_today_registrations()
    online_users = get_online_users()
    total_posts = get_total_posts()
    all_users = get_all_users()
    posts = get_all_posts()
    
    return render_template('admin_dashboard.html', 
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

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'users': get_total_users(),
        'posts': get_total_posts()
    })

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

@app.route('/music')
@login_required
def music():
    user = get_user_by_id(session['user_id'])
    return render_template('music.html', 
                         username=session['username'],
                         user_id=session['user_id'],
                         is_admin=session.get('is_admin', False),
                         is_premium=session.get('is_premium', False),
                         user_avatar=user['avatar'] if user else None)

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
    app.run(host='0.0.0.0', port=port, debug=True)