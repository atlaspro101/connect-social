import sqlite3
import os
from datetime import datetime
import hashlib

def reset_database():
    # Удаляем старую БД
    if os.path.exists('users.db'):
        os.remove('users.db')
        print("✓ Старая база данных удалена")
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Таблица пользователей
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
        theme_color TEXT DEFAULT 'purple',
        theme_background TEXT DEFAULT 'gradient',
        chat_wallpaper TEXT DEFAULT '',
        animations_enabled INTEGER DEFAULT 1,
        last_seen TIMESTAMP,
        created_at TIMESTAMP
    )''')
    print("✓ Таблица users создана")
    
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
    print("✓ Таблица posts создана")
    
    # Таблица комментариев
    c.execute('''CREATE TABLE comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        content TEXT,
        created_at TIMESTAMP
    )''')
    print("✓ Таблица comments создана")
    
    # Таблица лайков
    c.execute('''CREATE TABLE post_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        UNIQUE(post_id, user_id)
    )''')
    print("✓ Таблица post_likes создана")
    
    # Таблица подписчиков
    c.execute('''CREATE TABLE followers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id INTEGER,
        following_id INTEGER,
        created_at TIMESTAMP,
        UNIQUE(follower_id, following_id)
    )''')
    print("✓ Таблица followers создана")
    
    # Таблица чатов
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
    print("✓ Таблица chats создана")
    
    # Таблица сообщений (ВАЖНО!)
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
    print("✓ Таблица messages создана")
    
    # Таблица реакций
    c.execute('''CREATE TABLE message_reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        user_id INTEGER,
        reaction TEXT,
        created_at TIMESTAMP,
        UNIQUE(message_id, user_id)
    )''')
    print("✓ Таблица message_reactions создана")
    
    # Таблица блокировок
    c.execute('''CREATE TABLE blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blocker_id INTEGER,
        blocked_id INTEGER,
        created_at TIMESTAMP,
        UNIQUE(blocker_id, blocked_id)
    )''')
    print("✓ Таблица blocks создана")
    
    # Таблица жалоб
    c.execute('''CREATE TABLE reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_id INTEGER,
        reported_id INTEGER,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP
    )''')
    print("✓ Таблица reports создана")
    
    # Таблица достижений
    c.execute('''CREATE TABLE achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        icon TEXT,
        required_count INTEGER
    )''')
    print("✓ Таблица achievements создана")
    
    # Таблица полученных достижений
    c.execute('''CREATE TABLE user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        achievement_id INTEGER,
        earned_at TIMESTAMP,
        UNIQUE(user_id, achievement_id)
    )''')
    print("✓ Таблица user_achievements создана")
    
    # Таблица стикеров
    c.execute('''CREATE TABLE stickers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        image_url TEXT,
        category TEXT,
        is_premium INTEGER DEFAULT 0
    )''')
    print("✓ Таблица stickers создана")
    
    # Таблица избранных сообщений
    c.execute('''CREATE TABLE favorite_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message_id INTEGER,
        created_at TIMESTAMP,
        UNIQUE(user_id, message_id)
    )''')
    print("✓ Таблица favorite_messages создана")
    
    # Таблица QR сессий
    c.execute('''CREATE TABLE qr_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE,
        user_id INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP
    )''')
    print("✓ Таблица qr_sessions создана")
    
    # Таблица массовых уведомлений
    c.execute('''CREATE TABLE mass_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        message TEXT,
        sent_by TEXT,
        created_at TIMESTAMP
    )''')
    print("✓ Таблица mass_notifications создана")
    
    # Добавляем стандартные достижения
    achievements = [
        ('Первый пост', 'Опубликуйте свой первый пост', '📝', 1),
        ('Первый лайк', 'Получите первый лайк на свой пост', '❤️', 1),
        ('100 подписчиков', 'Соберите 100 подписчиков', '👥', 100),
        ('Мастер чата', 'Отправьте 1000 сообщений', '💬', 1000),
        ('Эксперт', 'Достигните 10 уровня', '⭐', 10),
    ]
    for a in achievements:
        c.execute("INSERT INTO achievements (name, description, icon, required_count) VALUES (?, ?, ?, ?)", a)
    print("✓ Достижения добавлены")
    
    # Создаем админа
    admin_pass = hashlib.sha256("fastyk26tyr".encode()).hexdigest()
    c.execute('''INSERT INTO users (username, password, full_name, is_admin, is_verified, created_at, last_seen) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              ("taranka", admin_pass, "Admin Taranka", 1, 1, datetime.now(), datetime.now()))
    print("✓ Админ создан: taranka / fastyk26tyr")
    
    conn.commit()
    conn.close()
    
    print("\n✅ База данных полностью пересоздана!")
    print("📝 Данные для входа:")
    print("   Логин: taranka")
    print("   Пароль: fastyk26tyr")

if __name__ == '__main__':
    reset_database()