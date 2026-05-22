import sqlite3
import hashlib
from datetime import datetime

print("🔄 Создание базы данных...")

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Таблица пользователей
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

# Таблица лайков
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

# Таблица сообщений (ВАЖНО!)
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
print("✓ Таблица messages создана")

# Таблица реакций
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

# Таблица QR сессий
c.execute('''CREATE TABLE IF NOT EXISTS qr_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE,
    user_id INTEGER,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP
)''')

# Таблица массовых уведомлений
c.execute('''CREATE TABLE IF NOT EXISTS mass_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    message TEXT,
    sent_by TEXT,
    created_at TIMESTAMP
)''')

# Добавляем достижения
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

print("✅ База данных успешно создана!")
print("📝 Данные для входа:")
print("   Логин: taranka")
print("   Пароль: fastyk26tyr")