"""
寻尤 - 付费聊天社交软件
Flask主程序
"""
import os
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from models import db, User, Message, Post, PostLike, Comment, Follow, Transaction, Report
from coin import RECHARGE_PACKAGES, recharge_coins, withdraw_coins, get_transaction_history, get_user_stats
from chat import send_message, get_chat_history, get_chat_list, mark_as_read, record_visitor, get_visitors, set_user_online
from admin_bp import admin_bp
from features_bp import features_bp

# 创建应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yan_yu_lang_secret_key_2024'
# 数据库路径：优先使用环境变量（PythonAnywhere等云平台），否则使用默认相对路径
_basedir = os.path.abspath(os.path.dirname(__file__))
_db_path = os.environ.get('DATABASE_PATH', os.path.join(_basedir, 'yan_yu_lang.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + _db_path
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024  # 上传限制128MB
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', os.path.join(_basedir, 'static', 'uploads'))
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# 初始化扩展
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', 
                    ping_timeout=60, ping_interval=25,
                    transports=['polling', 'websocket'],
                    manage_session=False)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    """处理未授权访问"""
    from flask import request
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    return redirect(url_for('login'))

# ==================== 辅助函数 ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_thumbnail(image_path, size=(300, 300)):
    """创建缩略图"""
    if not HAS_PIL:
        return
    try:
        img = Image.open(image_path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        img.save(image_path, quality=85)
    except Exception as e:
        print(f"缩略图创建失败: {e}")

# ==================== 页面路由 ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('splash'))

@app.route('/splash')
def splash():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('splash.html')

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('login.html', page='login')

@app.route('/register')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/setup-profile')
@login_required
def setup_profile():
    return render_template('login.html', page='setup')


@app.route('/vip')
@login_required
def vip_page():
    """诚意会员付费页面"""
    return render_template('vip.html')

# 男用户VIP权限检查装饰器
def require_vip_male(f):
    """男用户必须开通诚意会员才能访问"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.gender == 'male' and current_user.vip_type == 0 and not current_user.is_admin():
            return redirect(url_for('vip_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/home')
@login_required
def home():
    # 男用户未开通诚意会员，首页顶部显示VIP提示，不强制跳转

    # 直接后端查询用户列表，传给模板渲染
    target_gender = 'female' if current_user.gender == 'male' else 'male'
    users = User.query.filter_by(gender=target_gender).filter(User.id != current_user.id).order_by(User.is_online.desc(), User.last_active.desc()).limit(30).all()
    user_list = []
    for u in users:
        d = u.to_dict()
        d['tags'] = ['真诚', '有趣'] if u.is_online else ['神秘', '待发现']
        user_list.append(d)
    print(f"[DEBUG] home page: current_user={current_user.nickname}, gender={current_user.gender}, target={target_gender}, found={len(user_list)} users")
    return render_template('home.html', recommend_users=user_list)

@app.route('/test')
def test_page():
    return '<h1 style="color:red;font-size:40px;">V5 TEST OK!</h1>'

@app.route('/splash')
def splash_page():
    return render_template('splash.html')

@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    target_user = User.query.get(user_id)
    if not target_user:
        return redirect(url_for('home'))
    
    # 记录访客
    if current_user.id != user_id:
        record_visitor(current_user.id, user_id)
    
    return render_template('chat.html', target_user=target_user)

@app.route('/messages')
@login_required
def messages():
    return render_template('messages.html')

@app.route('/square')
@login_required
def square():
    return render_template('square.html')

@app.route('/post/<int:post_id>')
@login_required
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)

@app.route('/profile')
@login_required
def my_profile():
    result = render_template('profile.html', user=current_user, is_self=True)
    print(f"[DEBUG] profile rendered: {len(result)} chars, has body={'<body>' in result}, has style={'<style>' in result}, has header={'header-back' in result}")
    return result

@app.route('/user/<int:user_id>')
@login_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    is_self = (user_id == current_user.id)
    
    # 非本人访问记录访客
    if not is_self:
        record_visitor(current_user.id, user_id)
    
    return render_template('profile.html', user=user, is_self=is_self)

@app.route('/wallet')
@login_required
def wallet():
    return render_template('wallet.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/profile/edit')
@login_required
def edit_profile():
    return render_template('profile_edit.html', user=current_user)

@app.route('/visitors')
@login_required
def visitors():
    return render_template('visitors.html')

# ==================== API接口 ====================

# --- 认证相关 ---
@app.route('/api/register', methods=['POST'])
def api_register():
    """
    新注册流程 API
    支持6步注册：手机号密码 -> 性别 -> 昵称 -> 出生日期 -> 城市 -> 头像
    """
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    gender = data.get('gender')
    nickname = data.get('nickname')
    birthday = data.get('birthday')
    city = data.get('city')
    avatar = data.get('avatar')  # base64编码的头像
    
    # 验证必填字段
    if not all([phone, password, confirm_password, gender, nickname, birthday, city]):
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    # 验证密码
    if password != confirm_password:
        return jsonify({'success': False, 'message': '两次密码输入不一致'})
    
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码至少6位'})
    
    # 验证手机号格式
    if not phone.isdigit() or len(phone) != 11:
        return jsonify({'success': False, 'message': '请输入正确的11位手机号'})
    
    # 检查手机号是否已注册
    if User.query.filter_by(phone=phone).first():
        return jsonify({'success': False, 'message': '该手机号已注册'})
    
    # 验证性别
    if gender not in ['male', 'female']:
        return jsonify({'success': False, 'message': '请选择性别'})
    
    # 女用户必须上传头像
    if gender == 'female' and not avatar:
        return jsonify({'success': False, 'message': '请上传头像'})
    
    # 验证年龄 (出生日期格式: YYYY-MM-DD)
    print(f"[DEBUG] birthday value: '{birthday}', type: {type(birthday)}")
    try:
        birth_date = datetime.strptime(str(birthday).strip(), '%Y-%m-%d')
        age = (datetime.now() - birth_date).days // 365
        if age < 18:
            return jsonify({'success': False, 'message': '必须年满18岁才能注册'})
        if age > 100:
            return jsonify({'success': False, 'message': '请输入正确的出生日期'})
    except Exception as e:
        print(f"[DEBUG] birthday parse ERROR: {e}, repr: {repr(birthday)}")
        return jsonify({'success': False, 'message': f'出生日期解析失败: {e}'})
    
    # 处理头像上传
    avatar_url = '/static/uploads/avatars/default.png'
    if avatar and avatar.startswith('data:image'):
        try:
            import base64
            from PIL import Image
            from io import BytesIO
            
            # 解析 base64
            img_data = avatar.split(',')[1]
            img_bytes = base64.b64decode(img_data)
            img = Image.open(BytesIO(img_bytes))
            
            # 转换为RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 保存头像
            filename = f"avatar_{phone}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', filename)
            
            # 压缩和裁剪为正方形
            size = min(img.size)
            left = (img.width - size) // 2
            top = (img.height - size) // 2
            img = img.crop((left, top, left + size, top + size))
            img = img.resize((300, 300), Image.Resampling.LANCZOS)
            img.save(filepath, 'JPEG', quality=85)
            
            avatar_url = f'/static/uploads/avatars/{filename}'
        except Exception as e:
            print(f"头像保存失败: {e}")
    
    # 创建用户
    user = User(
        phone=phone,
        gender=gender,
        nickname=nickname,
        birthday=birthday,
        city=city,
        avatar=avatar_url,
        age=age,
        vip_type=1 if gender == 'female' else 0  # 女用户自动成为诚意会员
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    # 登录用户
    login_user(user)
    set_user_online(user.id, True)
    
    # 注册成功后自动生成虚拟访客记录（针对男用户）
    if gender == 'male':
        try:
            # 直接创建访客记录
            import random
            fake_visitors = User.query.filter(
                User.gender == 'female',
                User.id != user.id
            ).limit(5).all()
            
            count = min(random.randint(3, 5), len(fake_visitors))
            for fv in fake_visitors[:count]:
                from datetime import timedelta
                visitor_record = Visitor(
                    visitor_id=fv.id,
                    visited_id=user.id
                )
                visitor_record.created_at = datetime.utcnow() - timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                db.session.add(visitor_record)
            db.session.commit()
        except Exception as e:
            print(f"生成访客记录失败: {e}")
    
    # 返回结果
    if gender == 'male':
        return jsonify({
            'success': True, 
            'message': '注册成功',
            'need_vip': True,
            'redirect': '/vip'
        })
    else:
        return jsonify({
            'success': True, 
            'message': '注册成功',
            'need_vip': False,
            'redirect': '/home'
        })

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    
    user = User.query.filter_by(phone=phone).first()
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'message': '手机号或密码错误'})
    
    login_user(user)
    set_user_online(user.id, True)
    
    # 检查是否需要完善资料
    needs_profile = not user.nickname or user.nickname == ''
    
    return jsonify({
        'success': True, 
        'message': '登录成功',
        'needs_profile': needs_profile,
        'user': user.to_dict()
    })

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    set_user_online(current_user.id, False)
    logout_user()
    return jsonify({'success': True, 'message': '已退出登录'})



# --- 诚意会员 ---
@app.route('/api/become-vip', methods=['POST'])
@login_required
def api_become_vip():
    """开通诚意会员"""
    if current_user.vip_type > 0:
        return jsonify({'success': False, 'message': '您已经是诚意会员'})
    
    # 暂时：手动充值说明
    return jsonify({
        'success': False,
        'message': '请联系客服微信: xunyou_vip 开通诚意会员',
        'manual': True,
        'wechat': 'xunyou_vip',
        'price': 29
    })

@app.route('/api/check-vip', methods=['GET'])
@login_required
def api_check_vip():
    """检查VIP状态"""
    return jsonify({
        'success': True,
        'vip_type': current_user.vip_type,
        'is_vip': current_user.vip_type > 0,
        'is_sincere': current_user.vip_type >= 1
    })

@app.route('/logout')
def logout_page():
    if current_user.is_authenticated:
        try:
            set_user_online(current_user.id, False)
        except:
            pass
        logout_user()
    return redirect(url_for('login'))

@app.route('/api/check-phone', methods=['POST'])
def api_check_phone():
    phone = request.json.get('phone')
    user = User.query.filter_by(phone=phone).first()
    return jsonify({'exists': user is not None})

@app.route('/api/send-verify-code', methods=['POST'])
def api_send_verify_code():
    # 模拟发送验证码
    phone = request.json.get('phone')
    # 实际这里可以接入短信服务
    return jsonify({'success': True, 'message': '验证码已发送（模拟）', 'code': '1234'})

# --- 用户资料 ---
@app.route('/api/profile', methods=['POST'])
@login_required
def api_update_profile():
    data = request.json
    
    current_user.nickname = data.get('nickname', current_user.nickname)
    current_user.age = data.get('age', current_user.age)
    current_user.city = data.get('city', current_user.city)
    current_user.bio = data.get('bio', current_user.bio)
    current_user.interest_tags = data.get('interest_tags', current_user.interest_tags)
    
    if current_user.gender == 'female':
        current_user.chat_price = float(data.get('chat_price', 1.0))
    
    db.session.commit()
    return jsonify({'success': True, 'message': '资料更新成功', 'user': current_user.to_dict()})

@app.route('/api/user/<int:user_id>')
@login_required
def api_get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

# --- 首页推荐 ---
@app.route('/api/recommendations')
@login_required
def api_recommendations():
    # 获取女用户推荐列表
    query = User.query.filter_by(gender='female')
    
    # 筛选条件
    city = request.args.get('city')
    min_age = request.args.get('min_age', type=int)
    max_age = request.args.get('max_age', type=int)
    tags = request.args.get('tags')
    
    if city:
        query = query.filter(User.city.like(f'%{city}%'))
    if min_age:
        query = query.filter(User.age >= min_age)
    if max_age:
        query = query.filter(User.age <= max_age)
    
    users = query.order_by(User.is_online.desc(), User.last_active.desc()).limit(20).all()
    
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in users]
    })

# --- 附近用户 (首页列表) ---
@app.route('/api/users/nearby')
@login_required
def api_users_nearby():
    """获取首页用户列表，支持分页"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    gender = request.args.get('gender')
    city = request.args.get('city')
    online_only = request.args.get('online') == '1'
    
    # 获取目标性别用户
    target_gender = 'female' if current_user.gender == 'male' else 'male'
    
    if gender:
        query = User.query.filter_by(gender=gender)
    else:
        query = User.query.filter_by(gender=target_gender)
    
    # 排除自己
    query = query.filter(User.id != current_user.id)
    
    # 城市筛选
    if city:
        query = query.filter(User.city.like(f'%{city}%'))
    
    # 在线优先排序
    if online_only:
        query = query.filter_by(is_online=True)
    
    # 获取总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * per_page
    users = query.order_by(User.is_online.desc(), User.last_active.desc()).offset(offset).limit(per_page).all()
    
    user_list = []
    for u in users:
        user_dict = u.to_dict()
        # 添加标签
        user_dict['tags'] = ['真诚', '有趣'] if u.is_online else ['神秘', '待发现']
        user_list.append(user_dict)
    
    return jsonify({
        'success': True,
        'users': user_list,
        'has_more': offset + len(users) < total,
        'total': total,
        'page': page,
        'per_page': per_page
    })

# --- 聊天相关 ---
@app.route('/api/chat/history/<int:user_id>')
@login_required
def api_chat_history(user_id):
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    history = get_chat_history(current_user.id, user_id, limit, offset)
    return jsonify({'success': True, 'messages': history})

@app.route('/api/chat/list')
@login_required
def api_chat_list():
    chat_list = get_chat_list(current_user.id)
    return jsonify({'success': True, 'chat_list': chat_list})

@app.route('/api/chat/send', methods=['POST'])
@login_required
def api_send_message():
    data = request.json
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    msg_type = data.get('msg_type', 'text')
    
    success, message, msg_obj = send_message(
        current_user.id, 
        receiver_id, 
        content, 
        msg_type
    )
    
    if success:
        return jsonify({
            'success': True, 
            'message': '发送成功',
            'data': msg_obj.to_dict() if msg_obj else None
        })
    else:
        return jsonify({'success': False, 'message': message})

@app.route('/api/chat/mark-read/<int:user_id>', methods=['POST'])
@login_required
def api_mark_read(user_id):
    mark_as_read(current_user.id, user_id)
    return jsonify({'success': True})

@app.route('/api/visitors')
@login_required
def api_visitors():
    visitors = get_visitors(current_user.id)
    return jsonify({'success': True, 'visitors': visitors})

# --- 用户互动 (喜欢/收藏) ---
@app.route('/api/like', methods=['POST'])
@login_required
def api_like_user():
    """对用户打招呼/喜欢"""
    data = request.json
    target_id = data.get('user_id')
    
    if not target_id:
        return jsonify({'success': False, 'message': '参数错误'})
    
    target_user = User.query.get(target_id)
    if not target_user:
        return jsonify({'success': False, 'message': '用户不存在'})
    
    # 这里可以添加喜欢记录到数据库
    # 目前只是模拟成功
    
    return jsonify({
        'success': True, 
        'message': '已送出招呼',
        'matched': False  # 可以后续添加匹配逻辑
    })

@app.route('/api/favorite', methods=['POST'])
@login_required
def api_favorite_user():
    """收藏/取消收藏用户"""
    data = request.json
    target_id = data.get('user_id')
    action = data.get('action', 'add')  # add or remove
    
    if not target_id:
        return jsonify({'success': False, 'message': '参数错误'})
    
    # 这里可以添加收藏记录到数据库
    # 目前只是模拟成功
    
    return jsonify({
        'success': True,
        'message': '收藏成功' if action == 'add' else '已取消收藏'
    })

@app.route('/api/messages/unread-count')
@login_required
def api_unread_count():
    """获取未读消息数量"""
    unread = Message.query.filter_by(
        receiver_id=current_user.id,
        is_read=False
    ).count()
    return jsonify({'success': True, 'count': unread})

# --- 动态广场 ---
@app.route('/api/posts')
@login_required
def api_posts():
    sort = request.args.get('sort', 'hot')  # hot or new
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = Post.query.filter_by(is_visible=True)
    
    if sort == 'hot':
        query = query.order_by(Post.like_count.desc(), Post.comment_count.desc())
    else:
        query = query.order_by(Post.created_at.desc())
    
    # 女用户动态优先
    posts = query.all()
    female_posts = [p for p in posts if p.author.gender == 'female']
    male_posts = [p for p in posts if p.author.gender == 'male']
    sorted_posts = female_posts + male_posts
    
    # 分页
    start = (page - 1) * per_page
    end = start + per_page
    paginated = sorted_posts[start:end]
    
    return jsonify({
        'success': True,
        'posts': [p.to_dict() for p in paginated],
        'has_more': end < len(sorted_posts)
    })

@app.route('/api/post/create', methods=['POST'])
@login_required
def api_create_post():
    content = request.form.get('content', '')
    images = request.files.getlist('images')
    
    if not content and not images:
        return jsonify({'success': False, 'message': '内容不能为空'})
    
    # 处理图片
    image_paths = []
    for img in images[:9]:  # 最多9张
        if img and allowed_file(img.filename):
            filename = f"{uuid.uuid4().hex}.{img.filename.rsplit('.', 1)[1].lower()}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'posts', filename)
            img.save(filepath)
            create_thumbnail(filepath)
            image_paths.append(f'/static/uploads/posts/{filename}')
    
    post = Post(
        user_id=current_user.id,
        content=content
    )
    post.set_images(image_paths)
    db.session.add(post)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '发布成功', 'post': post.to_dict()})

@app.route('/api/post/<int:post_id>/like', methods=['POST'])
@login_required
def api_like_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    existing_like = PostLike.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()
    
    if existing_like:
        db.session.delete(existing_like)
        post.like_count -= 1
        liked = False
    else:
        like = PostLike(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        post.like_count += 1
        liked = True
    
    db.session.commit()
    return jsonify({'success': True, 'liked': liked, 'like_count': post.like_count})

@app.route('/api/post/<int:post_id>/comment', methods=['POST'])
@login_required
def api_comment_post(post_id):
    data = request.json
    content = data.get('content')
    
    if not content:
        return jsonify({'success': False, 'message': '评论内容不能为空'})
    
    post = Post.query.get_or_404(post_id)
    comment = Comment(
        user_id=current_user.id,
        post_id=post_id,
        content=content
    )
    db.session.add(comment)
    post.comment_count += 1
    db.session.commit()
    
    return jsonify({'success': True, 'comment': comment.to_dict()})

@app.route('/api/post/<int:post_id>/comments')
@login_required
def api_post_comments(post_id):
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.desc()).all()
    return jsonify({'success': True, 'comments': [c.to_dict() for c in comments]})

# --- 金币系统 ---
@app.route('/api/wallet/recharge-packages')
@login_required
def api_recharge_packages():
    return jsonify({'success': True, 'packages': RECHARGE_PACKAGES})

@app.route('/api/wallet/recharge', methods=['POST'])
@login_required
def api_recharge():
    data = request.json
    package_id = data.get('package_id')
    
    success, message, coins = recharge_coins(current_user.id, package_id)
    
    if success:
        return jsonify({
            'success': True, 
            'message': message,
            'coins_added': coins,
            'balance': User.query.get(current_user.id).coin_balance
        })
    else:
        return jsonify({'success': False, 'message': message})

@app.route('/api/wallet/withdraw', methods=['POST'])
@login_required
def api_withdraw():
    data = request.json
    yuan_amount = float(data.get('amount', 0))
    
    success, message, actual = withdraw_coins(current_user.id, yuan_amount)
    
    if success:
        return jsonify({
            'success': True, 
            'message': message,
            'actual_coins': actual,
            'balance': User.query.get(current_user.id).coin_balance
        })
    else:
        return jsonify({'success': False, 'message': message})

@app.route('/api/wallet/transactions')
@login_required
def api_transactions():
    transactions = get_transaction_history(current_user.id)
    return jsonify({'success': True, 'transactions': transactions})

@app.route('/api/wallet/stats')
@login_required
def api_wallet_stats():
    stats = get_user_stats(current_user.id)
    return jsonify({'success': True, 'stats': stats})

# --- 关注 ---
@app.route('/api/user/<int:user_id>/follow', methods=['POST'])
@login_required
def api_follow_user(user_id):
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': '不能关注自己'})
    
    user = User.query.get_or_404(user_id)
    
    existing = Follow.query.filter_by(
        follower_id=current_user.id,
        followed_id=user_id
    ).first()
    
    if existing:
        db.session.delete(existing)
        followed = False
    else:
        follow = Follow(follower_id=current_user.id, followed_id=user_id)
        db.session.add(follow)
        followed = True
    
    db.session.commit()
    return jsonify({'success': True, 'followed': followed})

@app.route('/api/user/<int:user_id>/followers')
@login_required
def api_followers(user_id):
    user = User.query.get_or_404(user_id)
    followers = Follow.query.filter_by(followed_id=user_id).all()
    return jsonify({
        'success': True, 
        'followers': [{'user': f.follower.to_dict()} for f in followers]
    })

@app.route('/api/user/<int:user_id>/following')
@login_required
def api_following(user_id):
    user = User.query.get_or_404(user_id)
    following = Follow.query.filter_by(follower_id=user_id).all()
    return jsonify({
        'success': True, 
        'following': [{'user': f.followed.to_dict()} for f in following]
    })

@app.route('/api/user/<int:user_id>/is-following')
@login_required
def api_is_following(user_id):
    existing = Follow.query.filter_by(
        follower_id=current_user.id,
        followed_id=user_id
    ).first()
    return jsonify({'success': True, 'is_following': existing is not None})

# --- 上传 ---
@app.route('/api/upload/avatar', methods=['POST'])
@login_required
def api_upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'message': '没有文件'})
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    if file and allowed_file(file.filename):
        filename = f"avatar_{current_user.id}_{uuid.uuid4().hex}.{file.filename.rsplit('.', 1)[1].lower()}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', filename)
        file.save(filepath)
        create_thumbnail(filepath, size=(200, 200))
        
        # 更新用户头像
        current_user.avatar = f'/static/uploads/avatars/{filename}'
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': '上传成功',
            'avatar': current_user.avatar
        })
    
    return jsonify({'success': False, 'message': '不支持的文件格式'})

# --- 后台管理 ---
# ==================== SocketIO事件 ====================

@socketio.on('connect')
def on_connect():
    if current_user.is_authenticated:
        set_user_online(current_user.id, True)
        emit('connected', {'user_id': current_user.id})

@socketio.on('disconnect')
def on_disconnect():
    if current_user.is_authenticated:
        set_user_online(current_user.id, False)

@socketio.on('join')
def on_join(data):
    user_id = data.get('user_id')
    if user_id:
        room = f'user_{user_id}'
        join_room(room)
        emit('joined', {'room': room})

@socketio.on('leave')
def on_leave(data):
    user_id = data.get('user_id')
    if user_id:
        room = f'user_{user_id}'
        leave_room(room)

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    msg_type = data.get('msg_type', 'text')
    
    if not all([sender_id, receiver_id, content]):
        emit('error', {'message': '参数不完整'})
        return
    
    success, message, msg_obj = send_message(sender_id, receiver_id, content, msg_type)
    
    if success:
        # 发送给发送者确认
        emit('message_sent', {
            'success': True,
            'message': msg_obj.to_dict()
        })
        
        # 发送给接收者
        emit('new_message', {
            'success': True,
            'message': msg_obj.to_dict()
        }, room=f'user_{receiver_id}')
    else:
        emit('message_error', {
            'success': False,
            'message': message
        })

@socketio.on('typing')
def handle_typing(data):
    receiver_id = data.get('receiver_id')
    is_typing = data.get('is_typing', True)
    
    if receiver_id:
        emit('user_typing', {
            'user_id': current_user.id,
            'is_typing': is_typing
        }, room=f'user_{receiver_id}')

@socketio.on('mark_read')
def handle_mark_read(data):
    user_id = data.get('user_id')
    from_user_id = data.get('from_user_id')
    
    if user_id and from_user_id:
        mark_as_read(user_id, from_user_id)
        emit('messages_read', {
            'from_user_id': from_user_id
        }, room=f'user_{from_user_id}')

# ==================== 静态文件 ====================

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==================== 初始化 ====================

# 国内可用的占位图函数
def placeholder_image(width=200, height=200, bg='ff6b9d', text='Photo'):
    """生成本地占位图URL（通过Flask路由返回SVG）"""
    return f'/api/placeholder/{width}/{height}/{bg}?t={text}'

@app.route('/api/placeholder/<int:w>/<int:h>/<bg>')
def api_placeholder(w, h, bg):
    """占位图路由，返回SVG图片，不依赖外部CDN"""
    text = request.args.get('t', 'Photo')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (w, h, w, h)
    svg += '<rect width="%d" height="%d" fill="#%s"/>' % (w, h, bg)
    svg += '<text x="%d" y="%d" font-family="Arial" font-size="16" fill="white" text-anchor="middle" opacity="0.3">%s</text>' % (w//2, h//2, text)
    svg += '</svg>'
    return svg, 200, {'Content-Type': 'image/svg+xml', 'Cache-Control': 'public, max-age=86400'}

def init_db():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        
        # 创建管理员账号
        if not User.query.filter_by(phone='13800138000').first():
            admin = User(
                phone='13800138000',
                nickname='管理员',
                gender='male',
                bio='系统管理员',
                vip_type=1
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # 女用户头像列表（循环分配）- 使用国内可用图片
            avatar_list = [
                placeholder_image(200, 200, 'ff6b9d', '小美'),
                placeholder_image(200, 200, 'c44dff', 'Lily'),
                placeholder_image(200, 200, '4facfe', '琪琪'),
                placeholder_image(200, 200, 'ff6b9d', '甜心'),
                placeholder_image(200, 200, 'c44dff', '梦琪'),
                placeholder_image(200, 200, '4facfe', '小鱼'),
                placeholder_image(200, 200, 'ff6b9d', '糖糖'),
                placeholder_image(200, 200, 'c44dff', '安安'),
            ]

            # 女用户照片墙列表（循环分配）- 使用国内可用图片
            photo_sets = [
                f'["{placeholder_image(400, 500, "ff6b9d", "P1")}","{placeholder_image(400, 500, "c44dff", "P2")}","{placeholder_image(400, 500, "4facfe", "P3")}"]',
                f'["{placeholder_image(400, 500, "c44dff", "P1")}","{placeholder_image(400, 500, "ff6b9d", "P2")}","{placeholder_image(400, 500, "4facfe", "P3")}"]',
                f'["{placeholder_image(400, 500, "4facfe", "P1")}","{placeholder_image(400, 500, "ff6b9d", "P2")}","{placeholder_image(400, 500, "c44dff", "P3")}"]',
                f'["{placeholder_image(400, 500, "ff6b9d", "P1")}","{placeholder_image(400, 500, "4facfe", "P2")}","{placeholder_image(400, 500, "c44dff", "P3")}"]',
                f'["{placeholder_image(400, 500, "c44dff", "P1")}","{placeholder_image(400, 500, "4facfe", "P2")}","{placeholder_image(400, 500, "ff6b9d", "P3")}"]',
            ]
            
            test_users = [
                {'phone': '13800138001', 'nickname': '小美', 'gender': 'female', 'age': 22, 'city': '上海', 'bio': '喜欢拍照的小姐姐～互关哦💕', 'chat_price': 2.0, 'height': 165, 'occupation': '摄影师', 'interests': '["拍照","旅行","美食","瑜伽"]', 'looking_for': '希望找到真诚善良的小哥哥一起探索世界', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138002', 'nickname': 'Lily', 'gender': 'female', 'age': 24, 'city': '北京', 'bio': '健身爱好者 ✨ 每天都在变好', 'chat_price': 3.0, 'height': 168, 'occupation': '健身教练', 'interests': '["健身","跑步","游泳","冥想"]', 'looking_for': '找一个志同道合的他一起变得更好', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138003', 'nickname': '琪琪', 'gender': 'female', 'age': 21, 'city': '深圳', 'bio': '在校大学生 🎓 喜欢交朋友', 'chat_price': 1.0, 'height': 160, 'occupation': '大学生', 'interests': '["学习","音乐","电影","游戏"]', 'looking_for': '希望认识有趣的人，一起聊天学习', 'vip_type': 1, 'is_online': False},
                {'phone': '13800138004', 'nickname': '测试男', 'gender': 'male', 'age': 25, 'city': '广州', 'bio': '随便看看', 'coin_balance': 1000, 'height': 175, 'occupation': '程序员', 'interests': '["编程","游戏","电影","美食"]', 'looking_for': '找个聊得来的女生'},
                {'phone': '13800138005', 'nickname': '甜心柚子', 'gender': 'female', 'age': 23, 'city': '成都', 'bio': '川妹子来啦🌶️ 爱吃火锅爱聊天', 'chat_price': 2.0, 'height': 158, 'occupation': '美食博主', 'interests': '["美食","旅行","拍照","追剧"]', 'looking_for': '想找一个爱吃爱玩的小哥哥带我浪', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138006', 'nickname': '梦琪', 'gender': 'female', 'age': 20, 'city': '杭州', 'bio': '西湖边的小仙女🌸 等你来聊', 'chat_price': 1.5, 'height': 162, 'occupation': '幼师', 'interests': '["绘画","手工","看书","音乐"]', 'looking_for': '希望遇到一个温柔体贴的男生', 'vip_type': 1, 'is_online': False},
                {'phone': '13800138007', 'nickname': '小鱼儿', 'gender': 'female', 'age': 25, 'city': '南京', 'bio': '喜欢旅行和美食🌍 分享生活日常', 'chat_price': 2.5, 'height': 166, 'occupation': '旅游规划师', 'interests': '["旅行","美食","摄影","写作"]', 'looking_for': '想找一个爱旅行的他一起看世界', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138008', 'nickname': '糖糖', 'gender': 'female', 'age': 22, 'city': '武汉', 'bio': '甜品控🍰 会做蛋糕的小姐姐', 'chat_price': 2.0, 'height': 163, 'occupation': '烘焙师', 'interests': '["烘焙","美食","电影","音乐"]', 'looking_for': '想找一个能吃懂我蛋糕的他', 'vip_type': 1, 'is_online': False},
                {'phone': '13800138009', 'nickname': '安安', 'gender': 'female', 'age': 26, 'city': '重庆', 'bio': '辣妹子🔥 性格直爽好相处', 'chat_price': 3.0, 'height': 167, 'occupation': '销售经理', 'interests': '["唱歌","跳舞","旅游","美食"]', 'looking_for': '找个能陪我去吃火锅的男生', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138010', 'nickname': '念念', 'gender': 'female', 'age': 21, 'city': '长沙', 'bio': '奶茶续命🧋 快来找我聊天鸭', 'chat_price': 1.0, 'height': 159, 'occupation': '学生', 'interests': '["奶茶","追剧","追星","美食"]', 'looking_for': '想找一个和我一起嗑CP的小哥哥', 'vip_type': 1, 'is_online': False},
                {'phone': '13800138011', 'nickname': '苏苏', 'gender': 'female', 'age': 24, 'city': '苏州', 'bio': '温柔如水的江南姑娘🌿', 'chat_price': 2.0, 'height': 164, 'occupation': '会计', 'interests': '["看书","茶艺","园艺","汉服"]', 'looking_for': '找一个稳重顾家的男生', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138012', 'nickname': '阿喵', 'gender': 'female', 'age': 23, 'city': '广州', 'bio': '猫奴🐱 家有两只主子 来聊聊', 'chat_price': 1.5, 'height': 161, 'occupation': '设计师', 'interests': '["撸猫","设计","旅行","美食"]', 'looking_for': '想认识喜欢小动物的他', 'vip_type': 1, 'is_online': False},
                {'phone': '13800138013', 'nickname': '诗诗', 'gender': 'female', 'age': 27, 'city': '西安', 'bio': '古风爱好者🏮 喜欢汉服和诗词', 'chat_price': 2.5, 'height': 165, 'occupation': '文案策划', 'interests': '["汉服","诗词","茶艺","古风"]', 'looking_for': '找一个懂古风文化的男生', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138014', 'nickname': '晴天', 'gender': 'female', 'age': 22, 'city': '厦门', 'bio': '海边长大的女孩🌅 日落和海风', 'chat_price': 2.0, 'height': 166, 'occupation': '瑜伽教练', 'interests': '["瑜伽","游泳","海边","日落"]', 'looking_for': '想找一个能陪我看日落的他', 'vip_type': 1, 'is_online': False},
                {'phone': '13800138015', 'nickname': '可可', 'gender': 'female', 'age': 20, 'city': '昆明', 'bio': '春城的阳光女孩☀️ 超级话痨', 'chat_price': 1.0, 'height': 160, 'occupation': '学生', 'interests': '["聊天","旅游","美食","音乐"]', 'looking_for': '太无聊了，有没有人陪我聊天', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138016', 'nickname': '夜猫子', 'gender': 'female', 'age': 25, 'city': '北京', 'bio': '深夜才最清醒🌙 来陪我聊天吧', 'chat_price': 3.0, 'height': 164, 'occupation': '编辑', 'interests': '["写作","夜宵","电影","游戏"]', 'looking_for': '深夜睡不着，有人陪我聊天吗', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138017', 'nickname': '小鹿', 'gender': 'female', 'age': 23, 'city': '郑州', 'bio': '爱追剧爱嗑CP📺 来安利呀', 'chat_price': 1.5, 'height': 162, 'occupation': '行政', 'interests': '["追剧","综艺","美食","逛街"]', 'looking_for': '找个和我一起追剧嗑CP的他', 'vip_type': 1, 'is_online': False},
                {'phone': '13800138018', 'nickname': '橘子', 'gender': 'female', 'age': 22, 'city': '天津', 'bio': '天津卫的吃货🍜 煎饼果子来一套', 'chat_price': 2.0, 'height': 163, 'occupation': '护士', 'interests': '["美食","相声","旅游","唱歌"]', 'looking_for': '找个会讲笑话的男生', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138019', 'nickname': '米娅', 'gender': 'female', 'age': 24, 'city': '深圳', 'bio': '互联网打工人💻 下班后来聊天', 'chat_price': 2.5, 'height': 165, 'occupation': '产品经理', 'interests': '["互联网","健身","咖啡","电影"]', 'looking_for': '想认识同在互联网圈的他', 'vip_type': 1, 'is_online': False},
                {'phone': '13800138020', 'nickname': '桃子', 'gender': 'female', 'age': 21, 'city': '上海', 'bio': '迪士尼在逃公主👑 来找我玩', 'chat_price': 1.5, 'height': 157, 'occupation': '模特', 'interests': '["拍照","穿搭","迪士尼","音乐"]', 'looking_for': '有没有人带我去迪士尼', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138021', 'nickname': '默默', 'gender': 'female', 'age': 26, 'city': '大连', 'bio': '海边城市的生活🐾 很想认识你', 'chat_price': 2.0, 'height': 167, 'occupation': '人事', 'interests': '["海边","宠物","美食","电影"]', 'looking_for': '找个一起看海的人', 'vip_type': 1, 'is_online': False},
                {'phone': '13800138022', 'nickname': '小仙女', 'gender': 'female', 'age': 20, 'city': '青岛', 'bio': '啤酒节见🍺 青岛妹子来啦', 'chat_price': 1.0, 'height': 161, 'occupation': '空乘', 'interests': '["旅行","音乐","美食","摄影"]', 'looking_for': '有人约我喝啤酒吗', 'vip_type': 1, 'is_online': True},
                {'phone': '13800138023', 'nickname': '暖阳', 'gender': 'female', 'age': 28, 'city': '成都', 'bio': '知心大姐姐❤️ 什么都能聊', 'chat_price': 3.0, 'height': 168, 'occupation': '心理咨询师', 'interests': '["心理学","读书","旅行","美食"]', 'looking_for': '想找一个能交心的他', 'vip_type': 1, 'is_online': False},
            ]
            
            female_idx = 0
            for u_data in test_users:
                if u_data.get('gender') == 'female':
                    u_data['avatar'] = avatar_list[female_idx % len(avatar_list)]
                    u_data['photos'] = photo_sets[female_idx % len(photo_sets)]
                    female_idx += 1
                user = User(**u_data)
                user.set_password('123456')
                db.session.add(user)
            
            db.session.commit()
            
            # 添加测试动态数据（使用国内可用的占位图）
            test_posts = [
                {'user_id': 1, 'content': '今天天气真好，出门拍照啦📸 喜欢这种阳光明媚的感觉~'},
                {'user_id': 2, 'content': '健身第30天！感觉自己越来越自律了💪 有没有人一起打卡~'},
                {'user_id': 5, 'content': '刚吃了顿火锅，辣得嘴巴都肿了但是好爽🌶️ 四川人太幸福了！'},
                {'user_id': 7, 'content': '刚从南京旅行回来，分享一下美美的照片🌍 旅行真的会让人心情变好~'},
                {'user_id': 9, 'content': '周末约朋友唱歌，唱了一下午嗓子都哑了🎤 但好开心呀！'},
                {'user_id': 11, 'content': '今天泡了一壶好茶，安静地看了一本书📚 享受独处时光~'},
                {'user_id': 13, 'content': '穿汉服出门被好多人问在哪买的🏮 传统文化真的太美了！'},
                {'user_id': 15, 'content': '昆明果然是春城，鲜花到处都是💐 欢迎大家来玩呀~'},
                {'user_id': 16, 'content': '深夜码字中...灵感来了挡都挡不住🌙 你们也熬夜吗？'},
                {'user_id': 18, 'content': '天津早点真的绝了！煎饼果子配豆腐脑完美🍜 谁吃谁知道！'},
            ]
            import random as _r
            for p_data in test_posts:
                num_imgs = _r.choice([0, 1, 1, 2, 3])
                if num_imgs > 0:
                    # 使用国内可用的占位图
                    images = [placeholder_image(400, 400, _r.choice(['ff6b9d', 'c44dff', '4facfe']), f'IMG{i+1}') for i in range(num_imgs)]
                    post = Post(**p_data)
                    post.set_images(images)
                else:
                    post = Post(**p_data)
                db.session.add(post)
            
            db.session.commit()
            
            # 调用seed_data添加更多假用户和动态
            try:
                from seed_data import main as seed_main
                seed_main(app)
                print("额外测试数据添加完成")
            except Exception as e:
                print(f"添加额外数据失败: {e}")
            
            print("数据库初始化完成！")
            print("管理员账号: 13800138000 / admin123")
            print("测试女用户: 13800138001-23 / 123456 (部分设为在线)")
            print("测试男用户: 13800138004 / 123456 (余额1000金币)")

# 注册Blueprint（模块级别，确保WSGI部署时也能加载）
app.register_blueprint(features_bp)
app.register_blueprint(admin_bp)

# Auto git-pull on startup (for remote deployment)
def auto_git_pull():
    import subprocess
    try:
        result = subprocess.run(['git', 'pull'], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)), timeout=30)
        print(f"Auto git-pull: {result.stdout}")
    except Exception as e:
        print(f"Auto git-pull failed: {e}")

auto_git_pull()


# 确保上传目录存在
os.makedirs(os.path.join(_basedir, 'static', 'uploads', 'avatars'), exist_ok=True)
os.makedirs(os.path.join(_basedir, 'static', 'uploads', 'posts'), exist_ok=True)
os.makedirs(os.path.join(_basedir, 'static', 'uploads', 'photos'), exist_ok=True)

# 自动修复种子用户密码（仅执行一次）
_PASSWORDS_FIXED_FLAG = os.path.join(_basedir, '.passwords_fixed')
if not os.path.exists(_PASSWORDS_FIXED_FLAG):
    try:
        with app.app_context():
            _fix_hash = generate_password_hash('123456')
            _admin_hash = generate_password_hash('admin123')
            # 修复所有fake_开头的女用户密码
            db.session.execute(db.text("UPDATE users SET password_hash=:h WHERE phone LIKE 'fake_%'"), {'h': _fix_hash})
            # 修复测试男用户
            db.session.execute(db.text("UPDATE users SET password_hash=:h, coin_balance=9999 WHERE phone='13800138004'"), {'h': _fix_hash})
            # 修复管理员
            db.session.execute(db.text("UPDATE users SET password_hash=:h WHERE phone='13800138000'"), {'h': _admin_hash})
            # 修复注册测试号
            db.session.execute(db.text("UPDATE users SET coin_balance=9999 WHERE phone='13900001111'"))
            db.session.commit()
            # 写标记文件，避免重复执行
            with open(_PASSWORDS_FIXED_FLAG, 'w') as f:
                f.write('done')
            print("密码修复完成！")
    except Exception as e:
        print(f"密码修复跳过: {e}")


def api_fix_passwords():
    """One-time password fix endpoint"""
    from werkzeug.security import generate_password_hash
    try:
        fix_hash = generate_password_hash('123456')
        admin_hash = generate_password_hash('admin123')
        db.session.execute(db.text("UPDATE users SET password_hash=:h WHERE phone LIKE 'fake_%'"), {'h': fix_hash})
        db.session.execute(db.text("UPDATE users SET password_hash=:h, coin_balance=9999 WHERE phone='13800138004'"), {'h': fix_hash})
        db.session.execute(db.text("UPDATE users SET password_hash=:h WHERE phone='13800138000'"), {'h': admin_hash})
        db.session.execute(db.text("UPDATE users SET coin_balance=9999 WHERE phone='13900001111'"))
        db.session.commit()
        return 'Passwords fixed!'
    except Exception as e:
        return f'Error: {e}'
