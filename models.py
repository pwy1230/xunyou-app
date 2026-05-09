"""
数据库模型
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # male/female
    nickname = db.Column(db.String(50), nullable=False)
    avatar = db.Column(db.String(200), default='/static/uploads/avatars/default.png')
    age = db.Column(db.Integer, default=18)
    city = db.Column(db.String(50), default='')
    bio = db.Column(db.String(200), default='')  # 个性签名
    interest_tags = db.Column(db.Text, default='[]')  # JSON数组
    chat_price = db.Column(db.Float, default=1.0)  # 女用户每条消息价格
    coin_balance = db.Column(db.Float, default=0.0)  # 金币余额
    is_online = db.Column(db.Boolean, default=False)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

    photos = db.Column(db.Text, default='[]')  # JSON数组，照片URL列表
    height = db.Column(db.Integer)  # 身高cm
    occupation = db.Column(db.String(50))  # 职业
    interests = db.Column(db.Text, default='[]')  # JSON数组，兴趣标签
    looking_for = db.Column(db.String(100))  # 想找什么
    latitude = db.Column(db.Float, default=0)  # 纬度
    longitude = db.Column(db.Float, default=0)  # 经度
    is_vip = db.Column(db.Boolean, default=False)  # VIP会员标识
    birthday = db.Column(db.String(20))  # 出生日期 YYYY-MM-DD
    vip_type = db.Column(db.Integer, default=0)  # 会员类型: 0=无, 1=诚意会员
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', backref='followed', lazy='dynamic')
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower', lazy='dynamic')
    visitors = db.relationship('Visitor', foreign_keys='Visitor.visited_id', backref='visited', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_interest_tags(self):
        try:
            return json.loads(self.interest_tags)
        except:
            return []
    
    def set_interest_tags(self, tags):
        self.interest_tags = json.dumps(tags)
    
    def is_admin(self):
        """判断是否为管理员"""
        return self.id == 1
    
    def get_photos(self):
        try: return json.loads(self.photos)
        except: return []
    
    def set_photos(self, photos):
        self.photos = json.dumps(photos)
    
    def get_interests(self):
        try: return json.loads(self.interests)
        except: return []
    
    def to_dict(self):
        return {
            'id': self.id,
            'phone': self.phone,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'gender': self.gender,
            'age': self.age,
            'city': self.city,
            'bio': self.bio,
            'interest_tags': self.get_interest_tags(),
            'chat_price': self.chat_price,
            'coin_balance': self.coin_balance,
            'is_online': self.is_online,
            'is_vip': self.is_vip if hasattr(self, 'is_vip') else False,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'photos': self.get_photos(),
            'height': self.height,
            'occupation': self.occupation,
            'interests': self.get_interests(),
            'looking_for': self.looking_for,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'is_vip': self.is_vip if hasattr(self, 'is_vip') else False
        }


class Message(db.Model):
    """消息表"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    msg_type = db.Column(db.String(20), default='text')  # text/image/emotion
    coin_cost = db.Column(db.Float, default=0.0)  # 本条消息费用
    platform_fee = db.Column(db.Float, default=0.0)  # 平台抽成
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'msg_type': self.msg_type,
            'coin_cost': self.coin_cost,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Post(db.Model):
    """动态表"""
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text, default='[]')  # JSON数组
    like_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    is_visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    likes = db.relationship('PostLike', backref='post', lazy='dynamic')
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    
    def get_images(self):
        try:
            return json.loads(self.images)
        except:
            return []
    
    def set_images(self, images):
        self.images = json.dumps(images)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.content,
            'images': self.get_images(),
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'author': self.author.to_dict() if self.author else None
        }


class PostLike(db.Model):
    """动态点赞表"""
    __tablename__ = 'post_likes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Comment(db.Model):
    """评论表"""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    author = db.relationship('User', backref='comments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'post_id': self.post_id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'author': self.author.to_dict() if self.author else None
        }


class Follow(db.Model):
    """关注表"""
    __tablename__ = 'follows'
    
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Visitor(db.Model):
    """访客记录表"""
    __tablename__ = 'visitors'
    
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    visited_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    visitor = db.relationship('User', foreign_keys=[visitor_id], backref='visited_records')
    visited_user = db.relationship('User', foreign_keys=[visited_id], backref='visitor_records')


class Transaction(db.Model):
    """交易记录表"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # recharge/consume/withdraw/income
    amount = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'amount': self.amount,
            'balance_after': self.balance_after,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Report(db.Model):
    """举报表"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reported_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending/processed/ignored
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SignInLog(db.Model):
    """签到记录表"""
    __tablename__ = 'sign_in_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    coins_earned = db.Column(db.Integer, default=5)
    consecutive_days = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'coins_earned': self.coins_earned,
            'consecutive_days': self.consecutive_days,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Announcement(db.Model):
    """公告表"""
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SensitiveWord(db.Model):
    """敏感词表"""
    __tablename__ = 'sensitive_words'
    
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50), default='custom')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
