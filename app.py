import os
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_from_directory
import hashlib
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta

# Импорт из database.py
from database import (
    init_db, add_user, get_user, get_user_by_id, update_last_seen,
    add_post, get_all_posts, get_user_posts, add_comment, get_comments,
    like_post, has_liked_post, unlike_post, follow_user, unfollow_user,
    is_following, get_followers_count, get_following_count, search_users,
    update_user_profile, delete_post, get_all_users, get_total_users,
    get_today_registrations, get_online_users, get_total_posts,
    make_admin, remove_admin, make_premium, get_or_create_chat,
    send_message, get_messages, get_unread_count, get_user_chats,
    create_call, update_call_status, get_active_call, get_call, hash_password
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

# ========== ФИЛЬТРЫ ДЛЯ ШАБЛОНОВ ==========
@app.template_filter('format_time')
def format_time_filter(date_value):
    if not date_value:
        return ""
    if isinstance(date_value, datetime):
        return date_value.strftime('%d.%m.%Y %H:%M')
    try:
        date_obj = datetime.strptime(str(date_value), '%Y-%m-%d %H:%M:%S.%f')
        return date_obj.strftime('%d.%m.%Y %H:%M')
    except:
        return str(date_value)[:16]

@app.template_filter('format_date')
def format_date_filter(date_value):
    if not date_value:
        return "январь 2026 г."
    if isinstance(date_value, datetime):
        months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        return f"{months[date_value.month - 1]} {date_value.year} г."
    try:
        date_obj = datetime.strptime(str(date_value), '%Y-%m-%d %H:%M:%S.%f')
        months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        return f"{months[date_obj.month - 1]} {date_obj.year} г."
    except:
        return "январь 2026 г."

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
        liked = False
    else:
        like_post(post_id, session['user_id'])
        liked = True
    
    posts = get_all_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    return jsonify({'liked': liked, 'likes_count': post['likes'] if post else 0})

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
    delete_post(post_id, session['user_id'])
    return jsonify({'success': True})

@app.route('/admin/make_admin/<int:user_id>', methods=['POST'])
@admin_required
def admin_make_admin(user_id):
    user = get_user_by_id(user_id)
    if user and user['username'] != 'taranka':
        make_admin(user_id)
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/admin/remove_admin/<int:user_id>', methods=['POST'])
@admin_required
def admin_remove_admin(user_id):
    user = get_user_by_id(user_id)
    if user and user['username'] != 'taranka':
        remove_admin(user_id)
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/buy_premium', methods=['POST'])
@login_required
def buy_premium():
    make_premium(session['user_id'])
    session['is_premium'] = 1
    return jsonify({'success': True})

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
    return render_template('chat.html', 
                         other_user=other_user, 
                         messages=messages, 
                         username=session['username'], 
                         user_id=session['user_id'],
                         user_avatar=current_user['avatar'] if current_user else None)

@app.route('/send_message', methods=['POST'])
@login_required
def send_message_route():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    message = data.get('message', '')
    if message.strip():
        send_message(session['user_id'], receiver_id, message)
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
            'is_read': msg['is_read']
        })
    return jsonify(result)

@app.route('/api/unread_count')
@login_required
def api_unread_count():
    return jsonify({'count': get_unread_count(session['user_id'])})

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