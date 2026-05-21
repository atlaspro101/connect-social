import sqlite3
from datetime import datetime, timedelta
import hashlib
import json

DATABASE_PATH = 'users.db'

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Таблица пользователей (расширенная)
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
    
    # Таблица лайков
    c.execute('''CREATE TABLE IF NOT EXISTS post_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        UNIQUE(post_id, user_id)
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
    
    # Таблица участников группы
    c.execute('''CREATE TABLE IF NOT EXISTS group_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        user_id INTEGER,
        joined_at TIMESTAMP,
        FOREIGN KEY(chat_id) REFERENCES chats(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Таблица сообщений (расширенная)
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
        FOREIGN KEY(chat_id) REFERENCES chats(id),
        FOREIGN KEY(sender_id) REFERENCES users(id),
        FOREIGN KEY(receiver_id) REFERENCES users(id)
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
    
    # Таблица QR-сессий
    c.execute('''CREATE TABLE IF NOT EXISTS qr_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE,
        user_id INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP
    )''')
    
    # Вставляем стандартные достижения
    c.execute("SELECT id FROM achievements LIMIT 1")
    if not c.fetchone():
        achievements = [
            ('Первый пост', 'Опубликуйте свой первый пост', '📝', 1),
            ('Первый лайк', 'Получите первый лайк на свой пост', '❤️', 1),
            ('100 подписчиков', 'Соберите 100 подписчиков', '👥', 100),
            ('Мастер чата', 'Отправьте 1000 сообщений', '💬', 1000),
            ('Эксперт', 'Достигните 10 уровня', '⭐', 10),
            ('Активный', 'Заходите на сайт 30 дней подряд', '🔥', 30),
        ]
        for a in achievements:
            c.execute("INSERT INTO achievements (name, description, icon, required_count) VALUES (?, ?, ?, ?)", a)
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

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
        c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin, is_premium, is_verified, is_private, level, experience, email, phone, created_at, last_seen FROM users WHERE id=?", (user_id,))
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

def send_message(sender_id, receiver_id, message, reply_to=None):
    chat_id = get_or_create_chat(sender_id, receiver_id)
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (chat_id, sender_id, receiver_id, message, reply_to, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (chat_id, sender_id, receiver_id, message, reply_to or 0, datetime.now()))
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
    conn.close()
    
    result = []
    for msg in messages:
        msg_dict = dict(msg)
        # Получаем реакции для сообщения
        c2 = conn.cursor()
        c2.execute("SELECT reaction, COUNT(*) FROM message_reactions WHERE message_id = ? GROUP BY reaction", (msg_dict['id'],))
        reactions = {r[0]: r[1] for r in c2.fetchall()}
        msg_dict['reactions'] = reactions
        result.append(msg_dict)
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
        
        # Проверяем количество постов
        c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ?", (user_id,))
        posts_count = c.fetchone()[0]
        
        # Проверяем количество подписчиков
        c.execute("SELECT COUNT(*) FROM followers WHERE following_id = ?", (user_id,))
        followers_count = c.fetchone()[0]
        
        # Проверяем количество сообщений
        c.execute("SELECT COUNT(*) FROM messages WHERE sender_id = ?", (user_id,))
        messages_count = c.fetchone()[0]
        
        # Проверяем уровень
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

# ========== ФУНКЦИИ ДЛЯ QR ВХОДА ==========
def create_qr_session(session_id, user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO qr_sessions (session_id, user_id, created_at) VALUES (?, ?, ?)",
                  (session_id, user_id, datetime.now()))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_qr_session(session_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM qr_sessions WHERE session_id = ?", (session_id,))
        session = c.fetchone()
        conn.close()
        return dict(session) if session else None
    except:
        return None

def confirm_qr_session(session_id, user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE qr_sessions SET status = 'confirmed', user_id = ? WHERE session_id = ?", (user_id, session_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()