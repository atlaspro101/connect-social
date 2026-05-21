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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'users.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')

app = Flask(__name__)
app.secret_key = 'connect-secret-key-2026-render'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Создаем папки
os.makedirs(os.path.join(UPLOAD_FOLDER, 'photos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'gifs'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'voice'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'avatars'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'banners'), exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ========== KEEP-ALIVE ФУНКЦИЯ ==========
def keep_alive():
    url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')
    if url == 'http://localhost:5000':
        url = 'https://connectss-mapb.onrender.com'
    
    while True:
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[KEEP-ALIVE] {current_time} - Сервер активен")
            
            if 'onrender.com' in url:
                response = requests.get(url, timeout=10)
                print(f"[KEEP-ALIVE] Пинг успешен - статус: {response.status_code}")
            
        except Exception as e:
            print(f"[KEEP-ALIVE] Ошибка пинга: {e}")
        
        time.sleep(10)

def start_keep_alive():
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    print("[KEEP-ALIVE] Поток поддержания активности запущен!")

# ========== ФИЛЬТРЫ ДЛЯ ШАБЛОНОВ ==========
@app.template_filter('format_time')
def format_time_filter(date_value):
    if not date_value:
        return ""
    if isinstance(date_value, datetime):
        return date_value.strftime('%d.%m.%Y %H:%M')
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
        
        # Таблица для звонков
        c.execute('''CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller_id INTEGER,
            receiver_id INTEGER,
            call_type TEXT,
            status TEXT,
            started_at TIMESTAMP,
            ended_at TIMESTAMP
        )''')
        
        # Создаем админа
        admin_pass = hash_password("fastyk26tyr")
        c.execute('''INSERT INTO users (username, password, full_name, is_admin, created_at, last_seen) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  ("taranka", admin_pass, "Admin Taranka", 1, datetime.now(), datetime.now()))
        conn.commit()
    
    # Добавляем колонку is_premium если её нет
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0")
        conn.commit()
    except:
        pass
    
    conn.close()
    print("[DATABASE] База данных инициализирована")

init_db()

# ========== ФУНКЦИИ БД ==========
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def add_user(username, password, full_name, birthday, gender, bio, avatar):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, full_name, birthday, gender, bio, avatar, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (username, password, full_name or '', birthday or '', gender or '', bio or '', avatar or '', datetime.now(), datetime.now()))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_user(username, password):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin, is_premium FROM users WHERE username=? AND password=?", 
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
        c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin, is_premium, created_at, last_seen FROM users WHERE id=?", (user_id,))
        user = c.fetchone()
        conn.close()
        return user
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

def add_post(user_id, content, media_path=None, media_type=None):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO posts (user_id, content, media_path, media_type, created_at) VALUES (?, ?, ?, ?, ?)",
                  (user_id, content or '', media_path, media_type, datetime.now()))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_all_posts():
    try:
        conn = get_db()
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
            if isinstance(post_dict.get('created_at'), str):
                try:
                    post_dict['created_at'] = datetime.strptime(post_dict['created_at'], '%Y-%m-%d %H:%M:%S.%f')
                except:
                    post_dict['created_at'] = datetime.now()
            result.append(post_dict)
        return result
    except:
        return []

def get_user_posts(user_id):
    try:
        conn = get_db()
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
            if isinstance(post_dict.get('created_at'), str):
                try:
                    post_dict['created_at'] = datetime.strptime(post_dict['created_at'], '%Y-%m-%d %H:%M:%S.%f')
                except:
                    post_dict['created_at'] = datetime.now()
            result.append(post_dict)
        return result
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
            if isinstance(comment_dict.get('created_at'), str):
                try:
                    comment_dict['created_at'] = datetime.strptime(comment_dict['created_at'], '%Y-%m-%d %H:%M:%S.%f')
                except:
                    comment_dict['created_at'] = datetime.now()
            result.append(comment_dict)
        return result
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
        c.execute("SELECT id, username, full_name, bio, avatar, is_admin, is_premium FROM users WHERE username LIKE ? OR full_name LIKE ? LIMIT 20", 
                  (f'%{query}%', f'%{query}%'))
        users = c.fetchall()
        conn.close()
        return [dict(user) for user in users]
    except:
        return []

def update_user_profile(user_id, full_name=None, bio=None, birthday=None, gender=None, avatar=None, banner=None):
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
        conn.commit()
        conn.close()
    except:
        pass

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
        c.execute("SELECT id, username, full_name, is_admin, is_premium, created_at, last_seen FROM users ORDER BY created_at DESC")
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

# ========== ФУНКЦИИ ДЛЯ ЗВОНКОВ (упрощенные) ==========
def create_call(caller_id, receiver_id, call_type):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO calls (caller_id, receiver_id, call_type, status, started_at) VALUES (?, ?, ?, ?, ?)",
              (caller_id, receiver_id, call_type, 'waiting', datetime.now()))
    call_id = c.lastrowid
    conn.commit()
    conn.close()
    return call_id

def update_call_status(call_id, status):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("UPDATE calls SET status = ?, ended_at = ? WHERE id = ?", 
              (status, datetime.now() if status in ['ended', 'missed'] else None, call_id))
    conn.commit()
    conn.close()

def get_active_call(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM calls WHERE (caller_id = ? OR receiver_id = ?) AND status = 'waiting' ORDER BY started_at DESC LIMIT 1", 
              (user_id, user_id))
    call = c.fetchone()
    conn.close()
    if call:
        return {'id': call[0], 'caller_id': call[1], 'receiver_id': call[2], 'call_type': call[3], 'status': call[4], 'started_at': call[5], 'ended_at': call[6]}
    return None

def get_call(call_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM calls WHERE id = ?", (call_id,))
    call = c.fetchone()
    conn.close()
    if call:
        return {'id': call[0], 'caller_id': call[1], 'receiver_id': call[2], 'call_type': call[3], 'status': call[4], 'started_at': call[5], 'ended_at': call[6]}
    return None

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
        if not user or not user['is_admin']:
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
        
        avatar_path = None
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().timestamp()}_{username}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', filename)
                file.save(filepath)
                avatar_path = f'/static/uploads/avatars/{filename}'
        
        if add_user(username, password, full_name, birthday, gender, bio, avatar_path):
            return redirect(url_for('login'))
        else:
            return "Username already exists!"
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
        else:
            return "Invalid credentials!"
    return render_template('login.html')

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
                
                if ext in ['mp3', 'wav', 'ogg']:
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
                         unread_count=0)

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
                         unread_count=0)

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
    return render_template('chats.html', username=session['username'], unread_count=0, user_id=session['user_id'], is_admin=session.get('is_admin', False), is_premium=session.get('is_premium', False))

@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    other_user = get_user_by_id(user_id)
    if not other_user:
        return "User not found", 404
    return render_template('chat.html', other_user=other_user, username=session['username'], user_id=session['user_id'])

# ========== МАРШРУТЫ ДЛЯ ЗВОНКОВ ==========
@app.route('/api/call/start', methods=['POST'])
@login_required
def api_call_start():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    call_type = data.get('call_type')
    
    receiver = get_user_by_id(receiver_id)
    if not receiver:
        return jsonify({'success': False, 'error': 'Пользователь не найден'})
    
    # Проверяем, есть ли активный звонок
    active_call = get_active_call(receiver_id)
    if active_call:
        return jsonify({'success': False, 'error': 'Пользователь уже в звонке'})
    
    call_id = create_call(session['user_id'], receiver_id, call_type)
    return jsonify({'success': True, 'call_id': call_id})

@app.route('/api/call/check')
@login_required
def api_call_check():
    call = get_active_call(session['user_id'])
    if call:
        caller = get_user_by_id(call['caller_id'])
        return jsonify({
            'call': {
                'id': call['id'],
                'caller_id': call['caller_id'],
                'caller_name': caller['username'] if caller else 'Unknown',
                'call_type': call['call_type']
            }
        })
    return jsonify({'call': None})

@app.route('/api/call/accept', methods=['POST'])
@login_required
def api_call_accept():
    data = request.get_json()
    call_id = data.get('call_id')
    call = get_call(call_id)
    
    if call and call['status'] == 'waiting':
        update_call_status(call_id, 'active')
        return jsonify({'success': True, 'call': call})
    return jsonify({'success': False})

@app.route('/api/call/reject', methods=['POST'])
@login_required
def api_call_reject():
    data = request.get_json()
    call_id = data.get('call_id')
    update_call_status(call_id, 'missed')
    return jsonify({'success': True})

@app.route('/api/call/end', methods=['POST'])
@login_required
def api_call_end():
    data = request.get_json()
    call_id = data.get('call_id')
    update_call_status(call_id, 'ended')
    return jsonify({'success': True})

@app.route('/call/<int:call_id>')
@login_required
def call_page(call_id):
    call = get_call(call_id)
    if not call:
        return "Звонок не найден", 404
    
    other_user_id = call['caller_id'] if call['receiver_id'] == session['user_id'] else call['receiver_id']
    other_user = get_user_by_id(other_user_id)
    
    return render_template('call.html',
                         call_id=call_id,
                         call_type=call['call_type'],
                         other_username=other_user['username'],
                         other_avatar=other_user['avatar'],
                         is_caller=(call['caller_id'] == session['user_id']))

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'uptime': 'Running'
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    start_keep_alive()
    
    print("\n" + "="*50)
    print("🚀 CONNECT SOCIAL NETWORK STARTED")
    print("="*50)
    print(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Локальный адрес: http://localhost:5000")
    print(f"💾 База данных: {DATABASE_PATH}")
    print(f"📁 Папка загрузок: {UPLOAD_FOLDER}")
    print("="*50)
    print("[KEEP-ALIVE] Сервер будет пинговать себя каждые 10 секунд")
    print("[ЗВОНКИ] Функция звонков активирована")
    print("="*50 + "\n")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)