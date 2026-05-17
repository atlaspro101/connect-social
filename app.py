import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import hashlib
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta

# Определяем базовую директорию
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
os.makedirs(os.path.join(UPLOAD_FOLDER, 'chat_media'), exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'ogg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Функции для работы с БД
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                  created_at TIMESTAMP)''')
    
    # Таблица постов
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  content TEXT,
                  media_path TEXT,
                  media_type TEXT,
                  likes INTEGER DEFAULT 0,
                  created_at TIMESTAMP)''')
    
    # Таблица комментариев
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER,
                  user_id INTEGER,
                  content TEXT,
                  created_at TIMESTAMP)''')
    
    # Таблица лайков
    c.execute('''CREATE TABLE IF NOT EXISTS post_likes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER,
                  user_id INTEGER,
                  UNIQUE(post_id, user_id))''')
    
    # Таблица подписчиков
    c.execute('''CREATE TABLE IF NOT EXISTS followers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  follower_id INTEGER,
                  following_id INTEGER,
                  created_at TIMESTAMP,
                  UNIQUE(follower_id, following_id))''')
    
    # Создаем админа
    admin_pass = hash_password("fastyk26tyr")
    try:
        c.execute("INSERT INTO users (username, password, full_name, is_admin, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                  ("taranka", admin_pass, "Admin Taranka", 1, datetime.now(), datetime.now()))
        print("✓ Админ создан: taranka / fastyk26tyr")
    except:
        pass
    
    conn.commit()
    conn.close()

def add_user(username, password, full_name, birthday, gender, bio, avatar):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, full_name, birthday, gender, bio, avatar, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (username, password, full_name, birthday, gender, bio, avatar, datetime.now(), datetime.now()))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_user(username, password):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin FROM users WHERE username=? AND password=?", 
              (username, password))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, bio, avatar, banner, birthday, gender, is_admin, created_at, last_seen FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def update_last_seen(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET last_seen = ? WHERE id = ?", (datetime.now(), user_id))
    conn.commit()
    conn.close()

def add_post(user_id, content, media_path=None, media_type=None):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO posts (user_id, content, media_path, media_type, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, content, media_path, media_type, datetime.now()))
    post_id = c.lastrowid
    conn.commit()
    conn.close()
    return post_id

def get_all_posts():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT posts.*, users.username, users.avatar, users.full_name
                 FROM posts 
                 JOIN users ON posts.user_id = users.id 
                 ORDER BY posts.created_at DESC''')
    posts = c.fetchall()
    conn.close()
    
    result = []
    for post in posts:
        post_dict = dict(post)
        result.append(post_dict)
    return result

def get_user_posts(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT posts.*, users.username, users.avatar 
                 FROM posts 
                 JOIN users ON posts.user_id = users.id 
                 WHERE posts.user_id = ?
                 ORDER BY posts.created_at DESC''', (user_id,))
    posts = c.fetchall()
    conn.close()
    return [dict(post) for post in posts]

def add_comment(post_id, user_id, content):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO comments (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
              (post_id, user_id, content, datetime.now()))
    conn.commit()
    conn.close()

def get_comments(post_id):
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT comments.*, users.username, users.avatar 
                 FROM comments 
                 JOIN users ON comments.user_id = users.id 
                 WHERE comments.post_id = ? 
                 ORDER BY comments.created_at ASC''', (post_id,))
    comments = c.fetchall()
    conn.close()
    return [dict(comment) for comment in comments]

def like_post(post_id, user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)", (post_id, user_id))
        c.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def has_liked_post(post_id, user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def follow_user(follower_id, following_id):
    if follower_id == following_id:
        return False
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO followers (follower_id, following_id, created_at) VALUES (?, ?, ?)",
                  (follower_id, following_id, datetime.now()))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def unfollow_user(follower_id, following_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM followers WHERE follower_id = ? AND following_id = ?", 
              (follower_id, following_id))
    conn.commit()
    conn.close()

def is_following(follower_id, following_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM followers WHERE follower_id = ? AND following_id = ?", 
              (follower_id, following_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_followers_count(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM followers WHERE following_id = ?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_following_count(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM followers WHERE follower_id = ?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def search_users(query):
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, bio, avatar FROM users WHERE username LIKE ? OR full_name LIKE ? LIMIT 20", 
              (f'%{query}%', f'%{query}%'))
    users = c.fetchall()
    conn.close()
    return [dict(user) for user in users]

def update_user_profile(user_id, full_name=None, bio=None, birthday=None, gender=None, avatar=None, banner=None):
    conn = sqlite3.connect(DATABASE_PATH)
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

# Маршруты
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
                filename = secure_filename(f"{username}_{file.filename}")
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
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = user[8] if len(user) > 8 else 0
            update_last_seen(user[0])
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
    
    for post in posts:
        post['comments_count'] = len(get_comments(post['id']))
    
    return render_template('feed.html', 
                         username=session['username'], 
                         posts=posts, 
                         liked_posts=liked_posts,
                         user_id=session['user_id'],
                         is_admin=session.get('is_admin', False),
                         user_avatar=user.get('avatar') if user else None)

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
    
    for post in posts:
        post['comments_count'] = len(get_comments(post['id']))
    
    return render_template('profile.html', 
                         profile_user=user,
                         posts=posts,
                         followers_count=followers_count,
                         following_count=following_count,
                         is_following=is_following_user,
                         current_user_id=session['user_id'],
                         is_admin=session.get('is_admin', False),
                         user_avatar=current_user.get('avatar') if current_user else None,
                         session=session)

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
    return render_template('post_detail.html', post=post, comments=comments, username=session['username'])

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
        return jsonify({'liked': False, 'likes_count': 0})
    else:
        like_post(post_id, session['user_id'])
        posts = get_all_posts()
        post = next((p for p in posts if p['id'] == post_id), None)
        return jsonify({'liked': True, 'likes_count': post['likes'] if post else 0})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)