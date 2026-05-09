# admin_bp.py - 寻尤管理后台 Blueprint（独立模块，不改app.py现有代码）
import os, random, string, uuid, json
from datetime import datetime as dt, timedelta
from functools import wraps

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash
from models import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# 管理员账号密码（硬编码）
ADMIN_USERNAME = '13800138000'
ADMIN_PASSWORD = 'admin123'

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated

def api_admin_required(f):
    """API专用权限检查，未登录返回JSON错误"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated

# ==================== Admin Login ====================
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """独立登录页面"""
    if request.method == 'GET':
        return render_template('admin_login.html')
    
    # POST - 处理登录
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        session.permanent = True  # 持久化session
        return jsonify({'ok': True})
    else:
        return jsonify({'error': '账号或密码错误'}), 400

@admin_bp.route('/logout')
def admin_logout():
    """退出登录"""
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')

# ==================== Admin Page ====================
@admin_bp.route('/')
@admin_required
def admin_page():
    return render_template('admin.html')

# ==================== Stats ====================
@admin_bp.route('/api/stats')
@api_admin_required
def api_stats():
    total_users = db.session.execute(db.text("SELECT COUNT(*) FROM users")).scalar()
    today = dt.utcnow().strftime('%Y-%m-%d')
    today_users = db.session.execute(db.text("SELECT COUNT(*) FROM users WHERE DATE(created_at) = :d"), {'d': today}).scalar()
    total_posts = db.session.execute(db.text("SELECT COUNT(*) FROM posts")).scalar()
    total_recharge = 0
    try:
        r = db.session.execute(db.text("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='success'")).scalar()
        total_recharge = float(r or 0)
    except:
        pass
    trend = []
    for i in range(6, -1, -1):
        day_str = (dt.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
        cnt = db.session.execute(db.text("SELECT COUNT(*) FROM users WHERE DATE(created_at) = :d"), {'d': day_str}).scalar()
        trend.append({'date': day_str[5:], 'count': cnt})
    rows = db.session.execute(db.text("SELECT id, nickname, phone, created_at FROM users ORDER BY id DESC LIMIT 5")).fetchall()
    recent = [{'id': r[0], 'nickname': r[1] or '', 'phone': r[2] or '', 'created_at': str(r[3])[:16] if r[3] else ''} for r in rows]
    return jsonify({'total_users': total_users, 'today_users': today_users, 'total_posts': total_posts, 'total_recharge': total_recharge, 'trend': trend, 'recent_users': recent})

# ==================== Downloads ====================
@admin_bp.route('/api/downloads')
@api_admin_required
def api_downloads():
    try:
        rows = db.session.execute(db.text("SELECT id, nickname, phone, region, device_model, ip, created_at FROM downloads ORDER BY created_at DESC")).fetchall()
        items = [{'id': r[0], 'nickname': r[1] or '', 'phone': r[2] or '', 'region': r[3] or '', 'device': r[4] or '', 'ip': r[5] or '', 'created_at': str(r[6])[:16] if r[6] else ''} for r in rows]
        return jsonify({'downloads': items, 'total': len(items)})
    except Exception as e:
        return jsonify({'downloads': [], 'total': 0, 'error': str(e)})

# ==================== Verifications ====================
@admin_bp.route('/api/verifications')
@api_admin_required
def api_verifications():
    try:
        rows = db.session.execute(db.text("SELECT id, nickname, phone, COALESCE(real_name,''), COALESCE(id_card_number,''), COALESCE(id_card_front,''), COALESCE(id_card_back,''), created_at FROM users WHERE verify_status='pending' ORDER BY id DESC")).fetchall()
        items = [{'id': r[0], 'nickname': r[1] or '', 'phone': r[2] or '', 'real_name': r[3], 'id_card_number': r[4], 'id_card_front': r[5], 'id_card_back': r[6], 'created_at': str(r[7])[:16] if r[7] else ''} for r in rows]
        return jsonify({'verifications': items, 'total': len(items)})
    except Exception as e:
        return jsonify({'verifications': [], 'total': 0, 'error': str(e)})

@admin_bp.route('/api/user/<int:user_id>/verify-approve', methods=['POST'])
@api_admin_required
def api_verify_approve(user_id):
    db.session.execute(db.text("UPDATE users SET verify_status='approved' WHERE id=:id"), {'id': user_id})
    db.session.commit()
    return jsonify({'ok': True})

@admin_bp.route('/api/user/<int:user_id>/verify-reject', methods=['POST'])
@api_admin_required
def api_verify_reject(user_id):
    db.session.execute(db.text("UPDATE users SET verify_status='rejected' WHERE id=:id"), {'id': user_id})
    db.session.commit()
    return jsonify({'ok': True})

# ==================== Users ====================
@admin_bp.route('/api/users')
@api_admin_required
def api_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    where = "WHERE phone NOT LIKE 'fake_%'"
    params = {}
    if search:
        where += " AND (nickname LIKE :s OR phone LIKE :s)"
        params['s'] = f'%{search}%'
    total = db.session.execute(db.text(f"SELECT COUNT(*) FROM users {where}"), params).scalar()
    params['lim'] = per_page
    params['off'] = (page - 1) * per_page
    rows = db.session.execute(db.text(f"SELECT id, nickname, phone, gender, vip_type, avatar, created_at, COALESCE(is_banned,0), COALESCE(verify_status,'none') FROM users {where} ORDER BY id DESC LIMIT :lim OFFSET :off"), params).fetchall()
    items = [{'id': r[0], 'nickname': r[1] or '', 'phone': r[2] or '', 'gender': r[3] or '', 'vip_type': r[4], 'avatar': r[5] or '', 'created_at': str(r[6])[:16] if r[6] else '', 'is_banned': bool(r[7]), 'verify_status': r[8]} for r in rows]
    return jsonify({'users': items, 'total': total, 'page': page})

@admin_bp.route('/api/user/<int:user_id>/toggle-vip', methods=['POST'])
@api_admin_required
def api_toggle_vip(user_id):
    row = db.session.execute(db.text("SELECT vip_type FROM users WHERE id=:id"), {'id': user_id}).fetchone()
    if not row:
        return jsonify({'error': '\u7528\u6237\u4e0d\u5b58\u5728'}), 404
    new_vip = 0 if row[0] else 1
    db.session.execute(db.text("UPDATE users SET vip_type=:v WHERE id=:id"), {'v': new_vip, 'id': user_id})
    db.session.commit()
    return jsonify({'ok': True, 'vip_type': new_vip})

@admin_bp.route('/api/user/<int:user_id>/toggle-ban', methods=['POST'])
@api_admin_required
def api_toggle_ban(user_id):
    row = db.session.execute(db.text("SELECT COALESCE(is_banned,0) FROM users WHERE id=:id"), {'id': user_id}).fetchone()
    if not row:
        return jsonify({'error': '\u7528\u6237\u4e0d\u5b58\u5728'}), 404
    new_ban = 0 if row[0] else 1
    db.session.execute(db.text("UPDATE users SET is_banned=:b WHERE id=:id"), {'b': new_ban, 'id': user_id})
    db.session.commit()
    return jsonify({'ok': True, 'is_banned': bool(new_ban)})

@admin_bp.route('/api/user/<int:user_id>/delete', methods=['POST'])
@api_admin_required
def api_delete_user(user_id):
    db.session.execute(db.text("DELETE FROM users WHERE id=:id"), {'id': user_id})
    db.session.commit()
    return jsonify({'ok': True})

@admin_bp.route('/api/user/<int:user_id>/edit', methods=['POST'])
@api_admin_required
def api_edit_user(user_id):
    """编辑用户资料"""
    from models import User
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    data = request.get_json() or {}
    
    # 可编辑字段
    if 'nickname' in data:
        user.nickname = data['nickname'][:50] if data['nickname'] else ''
    if 'avatar' in data:
        user.avatar = data['avatar'][:200] if data['avatar'] else ''
    if 'height' in data:
        try:
            user.height = int(data['height']) if data['height'] else None
        except:
            pass
    if 'occupation' in data:
        user.occupation = data['occupation'][:50] if data['occupation'] else ''
    if 'interests' in data:
        if isinstance(data['interests'], list):
            user.interests = json.dumps(data['interests'])
        elif isinstance(data['interests'], str):
            user.interests = json.dumps([x.strip() for x in data['interests'].split(',') if x.strip()])
    if 'looking_for' in data:
        user.looking_for = data['looking_for'][:100] if data['looking_for'] else ''
    if 'city' in data:
        user.city = data['city'][:50] if data['city'] else ''
    if 'bio' in data:
        user.bio = data['bio'][:200] if data['bio'] else ''
    if 'photos' in data:
        if isinstance(data['photos'], list):
            user.set_photos(data['photos'])
    
    db.session.commit()
    return jsonify({'ok': True, 'user': user.to_dict()})

@admin_bp.route('/api/user/<int:user_id>', methods=['GET'])
@api_admin_required
def api_get_user(user_id):
    """获取单个用户信息"""
    from models import User
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({'user': user.to_dict()})

# ==================== Fake Users ====================
@admin_bp.route('/api/fake-users')
@api_admin_required
def api_fake_users():
    rows = db.session.execute(db.text("SELECT id, nickname, gender, birthday, city, avatar, COALESCE(is_online,1), created_at, COALESCE(photos,'[]') FROM users WHERE phone LIKE 'fake_%' ORDER BY id DESC")).fetchall()
    items = []
    for r in rows:
        age = 0
        if r[3] and len(str(r[3])) >= 4:
            try:
                age = dt.utcnow().year - int(str(r[3])[:4])
            except:
                pass
        photos_list = []
        try:
            photos_list = json.loads(r[8]) if r[8] else []
        except:
            photos_list = []
        items.append({'id': r[0], 'nickname': r[1] or '', 'gender': r[2] or '', 'age': age, 'city': r[4] or '', 'avatar': r[5] or '', 'is_online': bool(r[6]), 'created_at': str(r[7])[:16] if r[7] else '', 'photos': photos_list})
    return jsonify({'fake_users': items})

@admin_bp.route('/api/fake-user', methods=['POST'])
@api_admin_required
def api_create_fake_user():
    nickname = request.form.get('nickname', '')
    gender = request.form.get('gender', 'female')
    age = request.form.get('age', '22')
    city = request.form.get('city', '')
    bio = request.form.get('bio', '')
    fake_phone = 'fake_' + ''.join(random.choices(string.digits, k=6))
    avatar_path = '/static/uploads/avatars/default.png'
    avatar_file = request.files.get('avatar')
    if avatar_file and avatar_file.filename:
        ext = avatar_file.filename.rsplit('.', 1)[-1] if '.' in avatar_file.filename else 'jpg'
        fn = f"{uuid.uuid4().hex[:8]}.{ext}"
        save_p = os.path.join(PROJECT_DIR, 'static', 'uploads', 'avatars', fn)
        avatar_file.save(save_p)
        try:
            from PIL import Image
            img = Image.open(save_p)
            if img.width > 800 or img.height > 800:
                img.thumbnail((800, 800))
                img.save(save_p, quality=85)
        except:
            pass
        avatar_path = f'/static/uploads/avatars/{fn}'
    birthday = f"{dt.utcnow().year - int(age)}-01-01"
    pw_hash = generate_password_hash('fake123456')
    db.session.execute(db.text(
        "INSERT INTO users (phone,nickname,gender,birthday,city,bio,avatar,password_hash,vip_type,is_online,created_at) "
        "VALUES (:p,:n,:g,:b,:c,:bio,:a,:pw,1,1,datetime('now'))"),
        {'p': fake_phone, 'n': nickname, 'g': gender, 'b': birthday, 'c': city, 'bio': bio, 'a': avatar_path, 'pw': pw_hash})
    db.session.commit()
    uid = db.session.execute(db.text("SELECT id FROM users WHERE phone=:p"), {'p': fake_phone}).scalar()

    # 处理照片墙图片上传
    photo_urls = []
    photos_files = request.files.getlist('photos')
    for pf in photos_files:
        if pf and pf.filename:
            ext = pf.filename.rsplit('.', 1)[-1] if '.' in pf.filename else 'jpg'
            fn = f"{uuid.uuid4().hex[:8]}.{ext}"
            save_p = os.path.join(PROJECT_DIR, 'static', 'uploads', 'photos', fn)
            os.makedirs(os.path.dirname(save_p), exist_ok=True)
            pf.save(save_p)
            try:
                from PIL import Image
                img = Image.open(save_p)
                if img.width > 1200 or img.height > 1200:
                    img.thumbnail((1200, 1200))
                    img.save(save_p, quality=85)
            except:
                pass
            photo_urls.append(f'/static/uploads/photos/{fn}')

    # 更新用户的photos字段
    if photo_urls:
        db.session.execute(db.text("UPDATE users SET photos=:p WHERE id=:id"), {'p': json.dumps(photo_urls), 'id': uid})
        db.session.commit()

    return jsonify({'ok': True, 'id': uid, 'phone': fake_phone})

@admin_bp.route('/api/fake-user/<int:user_id>/delete', methods=['POST'])
@api_admin_required
def api_delete_fake_user(user_id):
    row = db.session.execute(db.text("SELECT phone FROM users WHERE id=:id"), {'id': user_id}).fetchone()
    if not row or not row[0].startswith('fake_'):
        return jsonify({'error': '\u5047\u4eba\u4e0d\u5b58\u5728'}), 404
    db.session.execute(db.text("DELETE FROM users WHERE id=:id"), {'id': user_id})
    db.session.commit()
    return jsonify({'ok': True})

@admin_bp.route('/api/fake-users/toggle-online', methods=['POST'])
@api_admin_required
def api_fake_toggle_online():
    data = request.get_json()
    online = data.get('online', True)
    ids = data.get('ids', [])
    if ids:
        for uid in ids:
            db.session.execute(db.text("UPDATE users SET is_online=:o WHERE id=:id AND phone LIKE 'fake_%'"), {'o': int(online), 'id': uid})
    else:
        db.session.execute(db.text("UPDATE users SET is_online=:o WHERE phone LIKE 'fake_%'"), {'o': int(online)})
    db.session.commit()
    return jsonify({'ok': True})

# ==================== Posts ====================
@admin_bp.route('/api/posts')
@api_admin_required
def api_posts():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    total = db.session.execute(db.text("SELECT COUNT(*) FROM posts")).scalar()
    rows = db.session.execute(db.text(
        "SELECT p.id, p.content, p.user_id, p.created_at, COALESCE(u.nickname,'\u672a\u77e5') "
        "FROM posts p LEFT JOIN users u ON p.user_id=u.id ORDER BY p.id DESC LIMIT :lim OFFSET :off"),
        {'lim': per_page, 'off': (page-1)*per_page}).fetchall()
    items = [{'id': r[0], 'content': (r[1] or '')[:80], 'author': r[4], 'created_at': str(r[3])[:16] if r[3] else ''} for r in rows]
    return jsonify({'posts': items, 'total': total, 'page': page})

@admin_bp.route('/api/post/<int:post_id>/delete', methods=['POST'])
@api_admin_required
def api_delete_post(post_id):
    db.session.execute(db.text("DELETE FROM posts WHERE id=:id"), {'id': post_id})
    db.session.commit()
    return jsonify({'ok': True})

# ==================== Payments ====================
@admin_bp.route('/api/payments')
@api_admin_required
def api_payments():
    try:
        rows = db.session.execute(db.text(
            "SELECT p.id, p.user_id, p.amount, p.payment_type, p.status, p.created_at, COALESCE(u.nickname,'\u672a\u77e5') "
            "FROM payments p LEFT JOIN users u ON p.user_id=u.id ORDER BY p.created_at DESC")).fetchall()
        items = [{'id': r[0], 'user_id': r[1], 'amount': float(r[2]) if r[2] else 0, 'payment_type': r[3] or '', 'status': r[4] or '', 'created_at': str(r[5])[:16] if r[5] else '', 'nickname': r[6]} for r in rows]
        total_amount = sum(i['amount'] for i in items)
        return jsonify({'payments': items, 'total': len(items), 'total_amount': total_amount})
    except Exception as e:
        return jsonify({'payments': [], 'total': 0, 'total_amount': 0, 'error': str(e)})

# ==================== Record Download ====================
@admin_bp.route('/api/download', methods=['POST'])
def api_record_download():
    data = request.get_json() or {}
    try:
        db.session.execute(db.text(
            "INSERT INTO downloads (nickname,phone,region,device_model,ip,created_at) "
            "VALUES (:n,:p,:r,:d,:ip,datetime('now'))"),
            {'n': data.get('nickname', ''), 'p': data.get('phone', ''), 'r': data.get('region', ''), 'd': data.get('device', ''), 'ip': request.remote_addr})
        db.session.commit()
    except:
        pass
    return jsonify({'ok': True})

# ==================== Reports (举报管理) ====================
@admin_bp.route('/api/reports')
@api_admin_required
def api_reports():
    """获取举报列表"""
    try:
        rows = db.session.execute(db.text(
            "SELECT r.id, r.reporter_id, r.reported_id, r.reason, r.status, r.created_at, "
            "COALESCE(u1.nickname,'未知') as reporter_nickname, "
            "COALESCE(u2.nickname,'未知') as reported_nickname "
            "FROM reports r "
            "LEFT JOIN users u1 ON r.reporter_id=u1.id "
            "LEFT JOIN users u2 ON r.reported_id=u2.id "
            "ORDER BY r.created_at DESC")).fetchall()
        items = []
        for r in rows:
            items.append({
                'id': r[0],
                'reporter_id': r[1],
                'reported_id': r[2],
                'reason': r[3] or '',
                'status': r[4] or 'pending',
                'created_at': str(r[5])[:16] if r[5] else '',
                'reporter_nickname': r[6],
                'reported_nickname': r[7]
            })
        return jsonify({'reports': items, 'total': len(items)})
    except Exception as e:
        return jsonify({'reports': [], 'total': 0, 'error': str(e)})


@admin_bp.route('/api/report/<int:report_id>/handle', methods=['POST'])
@api_admin_required
def api_handle_report(report_id):
    """处理举报：通过/驳回"""
    data = request.get_json() or {}
    action = data.get('action', '')
    report = db.session.execute(db.text("SELECT reported_id FROM reports WHERE id=:id"), {'id': report_id}).fetchone()
    if not report:
        return jsonify({'error': '举报不存在'}), 404
    reported_id = report[0]
    if action == 'approve':
        db.session.execute(db.text("UPDATE users SET is_banned=1 WHERE id=:id"), {'id': reported_id})
        db.session.execute(db.text("UPDATE reports SET status='processed' WHERE id=:id"), {'id': report_id})
        db.session.commit()
        return jsonify({'ok': True, 'message': '已封禁用户'})
    else:
        db.session.execute(db.text("UPDATE reports SET status='ignored' WHERE id=:id"), {'id': report_id})
        db.session.commit()
        return jsonify({'ok': True, 'message': '已驳回举报'})


# ==================== Announcements (公告管理) ====================
@admin_bp.route('/api/announcements')
@api_admin_required
def api_announcements():
    """获取公告列表"""
    from models import Announcement
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    items = [a.to_dict() for a in announcements]
    return jsonify({'announcements': items, 'total': len(items)})


@admin_bp.route('/api/announcement', methods=['POST'])
@api_admin_required
def api_create_announcement():
    """创建公告"""
    from models import Announcement
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    is_active = data.get('is_active', True)
    if not title or not content:
        return jsonify({'error': '标题和内容不能为空'}), 400
    announcement = Announcement(title=title, content=content, is_active=is_active)
    db.session.add(announcement)
    db.session.commit()
    return jsonify({'ok': True, 'announcement': announcement.to_dict()})


@admin_bp.route('/api/announcement/<int:ann_id>/toggle', methods=['POST'])
@api_admin_required
def api_toggle_announcement(ann_id):
    """启用/禁用公告"""
    from models import Announcement
    ann = Announcement.query.get(ann_id)
    if not ann:
        return jsonify({'error': '公告不存在'}), 404
    ann.is_active = not ann.is_active
    db.session.commit()
    return jsonify({'ok': True, 'is_active': ann.is_active})


@admin_bp.route('/api/announcement/<int:ann_id>', methods=['DELETE'])
@api_admin_required
def api_delete_announcement(ann_id):
    """删除公告"""
    from models import Announcement
    ann = Announcement.query.get(ann_id)
    if not ann:
        return jsonify({'error': '公告不存在'}), 404
    db.session.delete(ann)
    db.session.commit()
    return jsonify({'ok': True})


# ==================== Sensitive Words (敏感词管理) ====================
@admin_bp.route('/api/sensitive-words')
@api_admin_required
def api_sensitive_words():
    """获取敏感词列表"""
    from models import SensitiveWord
    words = SensitiveWord.query.order_by(SensitiveWord.created_at.desc()).all()
    items = [w.to_dict() for w in words]
    return jsonify({'words': items, 'total': len(items)})


@admin_bp.route('/api/sensitive-word', methods=['POST'])
@api_admin_required
def api_add_sensitive_word():
    """添加敏感词"""
    from models import SensitiveWord
    from sensitive_filter import reload_filter
    data = request.get_json() or {}
    word = data.get('word', '').strip()
    category = data.get('category', 'other')
    if not word:
        return jsonify({'error': '敏感词不能为空'}), 400
    existing = SensitiveWord.query.filter_by(word=word).first()
    if existing:
        return jsonify({'error': '敏感词已存在'}), 400
    sw = SensitiveWord(word=word, category=category)
    db.session.add(sw)
    db.session.commit()
    reload_filter()
    return jsonify({'ok': True, 'word': sw.to_dict()})


@admin_bp.route('/api/sensitive-word/<int:word_id>', methods=['DELETE'])
@api_admin_required
def api_delete_sensitive_word(word_id):
    """删除敏感词"""
    from models import SensitiveWord
    from sensitive_filter import reload_filter
    sw = SensitiveWord.query.get(word_id)
    if not sw:
        return jsonify({'error': '敏感词不存在'}), 404
    db.session.delete(sw)
    db.session.commit()
    reload_filter()
    return jsonify({'ok': True})


# ==================== Sign-in Logs (签到记录) ====================
@admin_bp.route('/api/signin-logs')
@api_admin_required
def api_signin_logs():
    """获取签到记录"""
    from models import SignInLog
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query = SignInLog.query.order_by(SignInLog.created_at.desc())
    total = query.count()
    logs = query.offset((page-1)*per_page).limit(per_page).all()
    items = []
    for log in logs:
        items.append({
            'id': log.id,
            'user_id': log.user_id,
            'coins_earned': log.coins_earned,
            'consecutive_days': log.consecutive_days,
            'created_at': log.created_at.isoformat() if log.created_at else None,
            'nickname': log.user.nickname if log.user else '未知'
        })
    return jsonify({'logs': items, 'total': total, 'page': page})


# ==================== Visitor Logs (访客记录) ====================
@admin_bp.route('/api/visitor-logs')
@api_admin_required
def api_visitor_logs():
    """获取访客记录"""
    from models import Visitor
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query = Visitor.query.order_by(Visitor.created_at.desc())
    total = query.count()
    visitors = query.offset((page-1)*per_page).limit(per_page).all()
    items = []
    for v in visitors:
        items.append({
            'id': v.id,
            'visitor_id': v.visitor_id,
            'visited_id': v.visited_id,
            'created_at': v.created_at.isoformat() if v.created_at else None,
            'visitor_nickname': v.visitor.nickname if v.visitor else '未知',
            'visited_nickname': v.visited_user.nickname if v.visited_user else '未知'
        })
    return jsonify({'visitors': items, 'total': total, 'page': page})

# ==================== 假数据生成 ====================

@admin_bp.route('/api/generate-fake-users', methods=['POST'])
@api_admin_required
def api_generate_fake_users():
    """生成假女用户"""
    from models import db, User
    import random, json
    
    count = request.json.get('count', 10) if request.is_json else 10
    count = min(count, 50)  # 最多50个
    
    FEMALE_NAMES = ['小美','Lily','琪琪','甜心','梦琪','小鱼','糖糖','安安','暖暖','小仙女','暖阳','小鹿','雪儿','可心','小喵','糖果','星儿','若若','小月','露露','豆豆','念念','小柒','桃子','芒果']
    CITIES = ['上海','北京','深圳','广州','成都','杭州','武汉','南京','重庆','西安','长沙','青岛','厦门','苏州','天津']
    OCCUPATIONS = ['大学生','模特','主播','白领','教师','护士','设计师','空姐','健身教练','网红','化妆师','摄影师','舞蹈老师','瑜伽教练']
    BIOS = ['喜欢拍照的小姐姐～互关哦💕','健身爱好者✨每天都在变好','在校大学生🎓喜欢交朋友','吃吃喝喝就是我的日常🧋','热爱生活，喜欢旅行🌍','深夜还在的人，一定有故事🌙','日常摸鱼🐟','喜欢音乐和咖啡☕','小城市的慢生活🌿','找个人聊聊天就好～','认真生活的女孩子💪','今天也要开开心心的🥰','温柔且坚定','人间清醒✨','喜欢猫猫狗狗🐱🐶']
    TAGS = ['陪玩','深夜聊天','王者荣耀','二次元','电影','同城','美食','旅行','健身','音乐','摄影','读书','瑜伽','电竞','追剧']
    LOOKING = ['有趣的灵魂','暖男','聊得来的人','真心的朋友','一起旅游的人','成熟稳重','阳光帅气','温柔的陪伴']
    
    def make_placeholder(width, height, bg, text):
        return f'/api/placeholder/{width}/{height}/{bg}?t={text}'
    
    existing = User.query.filter_by(gender='female').count()
    new_users = []
    
    for i in range(count):
        phone = f'13900{60000 + existing + i}'
        if User.query.filter_by(phone=phone).first():
            continue
        
        name = FEMALE_NAMES[(existing + i) % len(FEMALE_NAMES)]
        colors = ['ff6b9d','c44dff','4facfe']
        avatar = make_placeholder(200, 200, colors[i % 3], name[:2])
        photos = [make_placeholder(400, 500, random.choice(colors), f'P{j+1}') for j in range(random.randint(3,6))]
        
        user = User(
            phone=phone,
            gender='female',
            nickname=name,
            avatar=avatar,
            age=random.randint(19,28),
            city=random.choice(CITIES),
            bio=random.choice(BIOS),
            interest_tags=json.dumps(random.sample(TAGS, random.randint(2,5)), ensure_ascii=False),
            chat_price=random.choice([1.0,2.0,3.0,5.0]),
            coin_balance=random.randint(50,500),
            is_online=random.choice([True,True,False]),
            height=random.choice([158,160,162,163,165,167,168,170,172]),
            occupation=random.choice(OCCUPATIONS),
            interests=json.dumps(random.sample(TAGS, random.randint(2,5)), ensure_ascii=False),
            looking_for=random.choice(LOOKING),
            vip_type=1,
        )
        user.set_password('123456')
        user.set_photos(photos)
        db.session.add(user)
        new_users.append(user)
    
    db.session.commit()
    return jsonify({'success': True, 'message': f'成功生成{len(new_users)}个假女用户', 'count': len(new_users)})


@admin_bp.route('/api/generate-fake-posts', methods=['POST'])
@api_admin_required
def api_generate_fake_posts():
    """生成假动态"""
    from models import db, User, Post
    import random, json
    
    count = request.json.get('count', 10) if request.is_json else 10
    count = min(count, 50)
    
    CONTENTS = [
        '今天天气真好，出门拍照啦📸','分享一下今天的晚餐🍝','周末在家看电影🎬',
        '健身打卡💪今天也很努力','发现了一家超好吃的店😋','深夜emo中...',
        '今天心情不错~','无聊找个人聊天','新发型好看吗？','分享一首好听的歌🎵',
        '下雨天适合宅家☕','刚看完一部好电影推荐给大家','今天逛街买了好多东西🛍️',
        '早起打卡！','加班到深夜💼','和闺蜜出去玩啦','今天化了美美的妆💄',
        '分享一下我的猫🐱','周末去哪玩呢？','有人一起打游戏吗🎮',
    ]
    
    def make_placeholder(width, height, bg, text):
        colors = ['ff6b9d','c44dff','4facfe','43e97b','fa709a']
        color = random.choice(colors)
        return f'/api/placeholder/{width}/{height}/{color}?t={text}'
    
    females = User.query.filter_by(gender='female').all()
    if not females:
        return jsonify({'success': False, 'message': '没有女用户，请先生成假用户'}), 400
    
    new_posts = []
    for i in range(count):
        author = random.choice(females)
        num_images = random.choice([0,0,1,1,2,3])
        images = [make_placeholder(400, 400, 'ff6b9d', f'IMG{j+1}') for j in range(num_images)]
        
        post = Post(
            user_id=author.id,
            content=random.choice(CONTENTS),
            images=json.dumps(images) if images else '[]',
            like_count=random.randint(2,88),
            comment_count=random.randint(0,15),
            is_visible=True
        )
        db.session.add(post)
        new_posts.append(post)
    
    db.session.commit()
    return jsonify({'success': True, 'message': f'成功生成{len(new_posts)}条假动态', 'count': len(new_posts)})


@admin_bp.route('/api/generate-fake-visitors', methods=['POST'])
@api_admin_required
def api_generate_fake_visitors():
    """生成假访客记录"""
    from models import db, User, Visitor
    import random
    from datetime import timedelta
    
    count = request.json.get('count', 20) if request.is_json else 20
    count = min(count, 100)
    
    females = User.query.filter_by(gender='female').all()
    if not females:
        return jsonify({'success': False, 'message': '没有女用户，请先生成假用户'}), 400
    
    new_visitors = []
    for i in range(count):
        visitor = random.choice(females)
        visited = random.choice(females)
        if visitor.id == visited.id:
            continue
        v = Visitor(visitor_id=visitor.id, visited_id=visited.id)
        v.created_at = datetime.utcnow() - timedelta(
            hours=random.randint(0,72),
            minutes=random.randint(0,59)
        )
        db.session.add(v)
        new_visitors.append(v)
    
    db.session.commit()
    return jsonify({'success': True, 'message': f'成功生成{len(new_visitors)}条假访客', 'count': len(new_visitors)})
