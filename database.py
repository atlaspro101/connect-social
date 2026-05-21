import sqlite3
from datetime import datetime, timedelta
import hashlib

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Таблица пользователей
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
        is_premium INTEGER DEFAULT 0,
        last_seen TIMESTAMP,
        created_at TIMESTAMP
    )''')
    
    # Таблица подписчиков
    c.execute('''CREATE TABLE IF NOT EXISTS followers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id INTEGER,
        following_id INTEGER,
        created_at TIMESTAMP,
        UNIQUE(follower_id, following_id)
    )''')
    
    # Таблица постов
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        media_path TEXT,
        media_type TEXT,
        likes INTEGER DEFAULT 0,
        created_at TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Таблица комментариев
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        content TEXT,
        created_at TIMESTAMP,
        FOREIGN KEY(post_id) REFERENCES posts(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Таблица лайков на постах
    c.execute('''CREATE TABLE IF NOT EXISTS post_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        UNIQUE(post_id, user_id)
    )''')
    
    # Таблица лайков на комментариях
    c.execute('''CREATE TABLE IF NOT EXISTS comment_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comment_id INTEGER,
        user_id INTEGER,
        UNIQUE(comment_id, user_id)
    )''')
    
    # Таблица банов
    c.execute('''CREATE TABLE IF NOT EXISTS bans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        user_id INTEGER,
        reason TEXT,
        ban_until TIMESTAMP,
        created_at TIMESTAMP,
        FOREIGN KEY(admin_id) REFERENCES users(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Таблица чатов
    c.execute('''CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_id INTEGER,
        user2_id INTEGER,
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
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP,
        FOREIGN KEY(chat_id) REFERENCES chats(id),
        FOREIGN KEY(sender_id) REFERENCES users(id),
        FOREIGN KEY(receiver_id) REFERENCES users(id)
    )''')
    
    # Таблица звонков
    c.execute('''CREATE TABLE IF NOT EXISTS calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caller_id INTEGER,
        receiver_id INTEGER,
        call_type TEXT,
        status TEXT,
        started_at TIMESTAMP,
        ended_at TIMESTAMP,
        FOREIGN KEY(caller_id) REFERENCES users(id),
        FOREIGN KEY(receiver_id) REFERENCES users(id)
    )''')
    
    conn.commit()
    
    # Создаем админа
    admin_pass = hashlib.sha256("fastyk26tyr".encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username, password, full_name, is_admin, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                  ("taranka", admin_pass, "Admin Taranka", 1, datetime.now(), datetime.now()))
        print("✓ Админ создан: taranka / fastyk26tyr")
    except:
        pass
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password, full_name, birthday, gender, bio, avatar):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, full_name, birthday, gender, bio, avatar, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (username, password, full_name, birthday, gender, bio, avatar, datetime.now(), datetime.now()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin, is_premium FROM users WHERE username=? AND password=?", 
              (username, password))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin, is_premium, created_at, last_seen FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def update_last_seen(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET last_seen = ? WHERE id = ?", (datetime.now(), user_id))
    conn.commit()
    conn.close()

def update_user_profile(user_id, full_name=None, bio=None, birthday=None, gender=None, avatar=None, banner=None):
    conn = sqlite3.connect('users.db')
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
    conn.commit()
    conn.close()

def add_post(user_id, content, media_path=None, media_type=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO posts (user_id, content, media_path, media_type, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, content, media_path, media_type, datetime.now()))
    post_id = c.lastrowid
    conn.commit()
    conn.close()
    return post_id

def get_all_posts():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT posts.*, users.username, users.avatar, users.full_name, users.is_admin, users.is_premium
                 FROM posts 
                 JOIN users ON posts.user_id = users.id 
                 ORDER BY posts.created_at DESC''')
    posts = c.fetchall()
    conn.close()
    
    result = []
    for post in posts:
        post_dict = dict(post)
        if isinstance(post_dict['created_at'], str):
            post_dict['created_at'] = datetime.strptime(post_dict['created_at'], '%Y-%m-%d %H:%M:%S.%f')
        result.append(post_dict)
    return result

def get_user_posts(user_id):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT posts.*, users.username, users.avatar, users.full_name, users.is_admin, users.is_premium
                 FROM posts 
                 JOIN users ON posts.user_id = users.id 
                 WHERE posts.user_id = ?
                 ORDER BY posts.created_at DESC''', (user_id,))
    posts = c.fetchall()
    conn.close()
    
    result = []
    for post in posts:
        post_dict = dict(post)
        if isinstance(post_dict['created_at'], str):
            post_dict['created_at'] = datetime.strptime(post_dict['created_at'], '%Y-%m-%d %H:%M:%S.%f')
        result.append(post_dict)
    return result

def get_post(post_id):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT posts.*, users.username, users.avatar 
                 FROM posts 
                 JOIN users ON posts.user_id = users.id 
                 WHERE posts.id = ?''', (post_id,))
    post = c.fetchone()
    conn.close()
    if post:
        post_dict = dict(post)
        if isinstance(post_dict['created_at'], str):
            post_dict['created_at'] = datetime.strptime(post_dict['created_at'], '%Y-%m-%d %H:%M:%S.%f')
        return post_dict
    return None

def add_comment(post_id, user_id, content, voice_path=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO comments (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
              (post_id, user_id, content, datetime.now()))
    conn.commit()
    conn.close()

def get_comments(post_id):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT comments.*, users.username, users.avatar, users.is_admin, users.is_premium
                 FROM comments 
                 JOIN users ON comments.user_id = users.id 
                 WHERE comments.post_id = ? 
                 ORDER BY comments.created_at ASC''', (post_id,))
    comments = c.fetchall()
    conn.close()
    
    result = []
    for comment in comments:
        comment_dict = dict(comment)
        if isinstance(comment_dict['created_at'], str):
            comment_dict['created_at'] = datetime.strptime(comment_dict['created_at'], '%Y-%m-%d %H:%M:%S.%f')
        result.append(comment_dict)
    return result

def like_post(post_id, user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)", (post_id, user_id))
        c.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False
    finally:
        conn.close()

def unlike_post(post_id, user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
    c.execute("UPDATE posts SET likes = likes - 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

def has_liked_post(post_id, user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def follow_user(follower_id, following_id):
    if follower_id == following_id:
        return False
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO followers (follower_id, following_id, created_at) VALUES (?, ?, ?)",
                  (follower_id, following_id, datetime.now()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def unfollow_user(follower_id, following_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM followers WHERE follower_id = ? AND following_id = ?", 
              (follower_id, following_id))
    conn.commit()
    conn.close()

def is_following(follower_id, following_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id FROM followers WHERE follower_id = ? AND following_id = ?", 
              (follower_id, following_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_followers_count(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM followers WHERE following_id = ?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_following_count(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM followers WHERE follower_id = ?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def search_users(query):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, bio, avatar, is_admin, is_premium FROM users WHERE username LIKE ? OR full_name LIKE ? LIMIT 20", 
              (f'%{query}%', f'%{query}%'))
    users = c.fetchall()
    conn.close()
    return [dict(user) for user in users]

def get_online_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    five_min_ago = datetime.now() - timedelta(minutes=5)
    c.execute("SELECT COUNT(*) FROM users WHERE last_seen > ?", (five_min_ago,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_today_registrations():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    c.execute("SELECT COUNT(*) FROM users WHERE created_at > ?", (today,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_posts():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM posts")
    count = c.fetchone()[0]
    conn.close()
    return count

def delete_post(post_id, admin_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

def ban_user(admin_id, user_id, reason, hours):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    ban_until = datetime.now() + timedelta(hours=hours)
    c.execute("UPDATE users SET is_banned = 1, ban_reason = ?, ban_until = ? WHERE id = ?", 
              (reason, ban_until, user_id))
    c.execute("INSERT INTO bans (admin_id, user_id, reason, ban_until, created_at) VALUES (?, ?, ?, ?, ?)",
              (admin_id, user_id, reason, ban_until, datetime.now()))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 0, ban_reason = NULL, ban_until = NULL WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, is_admin, is_premium, created_at, last_seen FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    conn.close()
    return [dict(user) for user in users]

def is_user_banned(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT is_banned, ban_reason, ban_until FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == 1:
        if result[2]:
            ban_until = datetime.strptime(result[2], '%Y-%m-%d %H:%M:%S.%f')
            if ban_until > datetime.now():
                return {'banned': True, 'reason': result[1], 'until': ban_until}
    return {'banned': False}

def make_admin(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 0 WHERE id = ? AND username != 'taranka'", (user_id,))
    conn.commit()
    conn.close()

def make_premium(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_premium = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# ========== ФУНКЦИИ ДЛЯ ЧАТОВ ==========

def get_or_create_chat(user1_id, user2_id):
    conn = sqlite3.connect('users.db')
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

def send_message(sender_id, receiver_id, message, media_path=None):
    chat_id = get_or_create_chat(sender_id, receiver_id)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (chat_id, sender_id, receiver_id, message, media_path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (chat_id, sender_id, receiver_id, message, media_path, datetime.now()))
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return msg_id

def get_messages(user_id, other_user_id, limit=50):
    chat_id = get_or_create_chat(user_id, other_user_id)
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT messages.*, users.username, users.avatar 
                 FROM messages 
                 JOIN users ON messages.sender_id = users.id 
                 WHERE chat_id = ? 
                 ORDER BY messages.created_at ASC LIMIT ?''', (chat_id, limit))
    messages = c.fetchall()
    conn.close()
    
    result = []
    for msg in messages:
        msg_dict = dict(msg)
        if isinstance(msg_dict['created_at'], str):
            msg_dict['created_at'] = datetime.strptime(msg_dict['created_at'], '%Y-%m-%d %H:%M:%S.%f')
        result.append(msg_dict)
    return result

def mark_messages_as_read(chat_id, user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE messages SET is_read = 1 WHERE chat_id = ? AND receiver_id = ? AND is_read = 0",
              (chat_id, user_id))
    conn.commit()
    conn.close()

def get_unread_count(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_user_chats(user_id):
    conn = sqlite3.connect('users.db')
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
                    (SELECT message FROM messages WHERE chat_id = chats.id ORDER BY created_at DESC LIMIT 1) as last_message,
                    (SELECT created_at FROM messages WHERE chat_id = chats.id ORDER BY created_at DESC LIMIT 1) as last_message_time
                 FROM chats
                 JOIN users ON (CASE 
                        WHEN chats.user1_id = ? THEN chats.user2_id
                        ELSE chats.user1_id
                    END) = users.id
                 WHERE chats.user1_id = ? OR chats.user2_id = ?
                 ORDER BY last_message_time DESC''', (user_id, user_id, user_id, user_id))
    chats = c.fetchall()
    conn.close()
    return [dict(chat) for chat in chats]

# ========== ФУНКЦИИ ДЛЯ ЗВОНКОВ ==========

def create_call(caller_id, receiver_id, call_type):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO calls (caller_id, receiver_id, call_type, status, started_at) VALUES (?, ?, ?, ?, ?)",
              (caller_id, receiver_id, call_type, 'waiting', datetime.now()))
    call_id = c.lastrowid
    conn.commit()
    conn.close()
    return call_id

def update_call_status(call_id, status):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE calls SET status = ?, ended_at = ? WHERE id = ?", 
              (status, datetime.now() if status in ['ended', 'missed'] else None, call_id))
    conn.commit()
    conn.close()

def get_active_call(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM calls WHERE (caller_id = ? OR receiver_id = ?) AND status = 'waiting' ORDER BY started_at DESC LIMIT 1", 
              (user_id, user_id))
    call = c.fetchone()
    conn.close()
    return call

def get_call(call_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM calls WHERE id = ?", (call_id,))
    call = c.fetchone()
    conn.close()
    if call:
        return {
            'id': call[0],
            'caller_id': call[1],
            'receiver_id': call[2],
            'call_type': call[3],
            'status': call[4],
            'started_at': call[5],
            'ended_at': call[6]
        }
    return None