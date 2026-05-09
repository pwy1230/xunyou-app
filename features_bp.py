# features_bp.py - 闫雨浪新功能 Blueprint
import os
import random
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Visitor, SignInLog, Announcement

features_bp = Blueprint('features', __name__)

# ==================== 签到功能 ====================

@features_bp.route('/api/signin', methods=['POST'])
@login_required
def signin():
    """
    签到接口
    - 每天签到领5金币
    - 7天连续签到翻倍（第7天35金币）
    """
    user = User.query.get(current_user.id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    # 获取今天的签到记录
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_signin = SignInLog.query.filter(
        SignInLog.user_id == user.id,
        SignInLog.created_at >= today_start
    ).first()

    if today_signin:
        return jsonify({
            'success': False,
            'message': f'今日已签到，获得{today_signin.coins_earned}金币',
            'coins_earned': today_signin.coins_earned,
            'consecutive_days': today_signin.consecutive_days,
            'balance_after': user.coin_balance
        })

    # 计算连续签到天数
    yesterday = today_start - timedelta(days=1)
    yesterday_signin = SignInLog.query.filter(
        SignInLog.user_id == user.id,
        SignInLog.created_at >= yesterday,
        SignInLog.created_at < today_start
    ).first()

    if yesterday_signin:
        consecutive_days = yesterday_signin.consecutive_days + 1
    else:
        consecutive_days = 1

    # 计算金币（7天连续翻倍）
    if consecutive_days == 7:
        coins_earned = 35  # 第7天35金币
    else:
        coins_earned = 5

    # 创建签到记录
    signin_log = SignInLog(
        user_id=user.id,
        coins_earned=coins_earned,
        consecutive_days=consecutive_days
    )
    db.session.add(signin_log)

    # 更新用户金币
    user.coin_balance += coins_earned
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'签到成功！连续签到{consecutive_days}天',
        'coins_earned': coins_earned,
        'consecutive_days': consecutive_days,
        'balance_after': user.coin_balance
    })


@features_bp.route('/api/signin/status', methods=['GET'])
@login_required
def signin_status():
    """获取签到状态"""
    user = User.query.get(current_user.id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_signin = SignInLog.query.filter(
        SignInLog.user_id == user.id,
        SignInLog.created_at >= today_start
    ).first()

    if today_signin:
        return jsonify({
            'signed_today': True,
            'coins_earned': today_signin.coins_earned,
            'consecutive_days': today_signin.consecutive_days,
            'balance': user.coin_balance
        })
    else:
        # 获取昨天的连续天数
        yesterday = today_start - timedelta(days=1)
        yesterday_signin = SignInLog.query.filter(
            SignInLog.user_id == user.id,
            SignInLog.created_at >= yesterday,
            SignInLog.created_at < today_start
        ).first()

        consecutive_days = yesterday_signin.consecutive_days if yesterday_signin else 0

        return jsonify({
            'signed_today': False,
            'coins_earned': 0,
            'consecutive_days': consecutive_days,
            'balance': user.coin_balance
        })


# ==================== 访客功能 ====================

@features_bp.route('/api/visitors', methods=['GET'])
@login_required
def get_visitors():
    """
    获取访客列表
    - 非VIP用户：头像模糊、信息半隐藏
    - VIP用户：完整信息
    """
    user = User.query.get(current_user.id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    visitors = Visitor.query.filter_by(visited_id=user.id).order_by(
        Visitor.created_at.desc()
    ).limit(20).all()

    visitor_list = []
    is_vip = user.vip_type > 0

    for v in visitors:
        visitor = v.visitor
        if not visitor:
            continue

        visitor_data = {
            'id': visitor.id,
            'nickname': visitor.nickname if is_vip else visitor.nickname[0] + '**',
            'avatar': visitor.avatar,
            'age': visitor.age,
            'city': visitor.city if is_vip else visitor.city[0] + '**',
            'gender': visitor.gender,
            'visited_at': v.created_at.isoformat() if v.created_at else None,
            'is_blurred': not is_vip  # 是否模糊显示
        }
        visitor_list.append(visitor_data)

    # 获取未读访客数（简化版：固定显示3）
    unread_count = 3 if len(visitor_list) > 0 else 0

    return jsonify({
        'success': True,
        'visitors': visitor_list,
        'unread_count': unread_count,
        'is_vip': is_vip
    })


def seed_visitors_data(user_id=None):
    """
    直接调用生成虚拟访客记录（供app.py注册后调用）
    """
    if user_id:
        user = User.query.get(user_id)
    else:
        user = User.query.get(current_user.id) if current_user.is_authenticated else None
    
    if not user:
        return {'success': False, 'error': '用户不存在'}

    existing_count = Visitor.query.filter_by(visited_id=user.id).count()
    if existing_count > 0:
        return {'success': True, 'message': '访客记录已存在', 'count': existing_count}

    fake_visitors = User.query.filter(
        User.gender == 'female',
        User.id != user.id
    ).limit(5).all()

    count = random.randint(3, 5)
    created = 0

    for i, fv in enumerate(fake_visitors[:count]):
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)

        visitor_record = Visitor(
            visitor_id=fv.id,
            visited_id=user.id
        )
        visitor_record.created_at = datetime.utcnow() - timedelta(
            hours=random_hours,
            minutes=random_minutes
        )
        db.session.add(visitor_record)
        created += 1

    if created < count and fake_visitors:
        for i in range(count - created):
            fv = random.choice(fake_visitors)
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

    return {
        'success': True,
        'message': f'已生成{count}条访客记录',
        'count': count
    }


@features_bp.route('/api/visitors/seed', methods=['POST'])
@login_required
def seed_visitors():
    """
    注册时调用，生成3-5条虚拟访客记录
    """
    return jsonify(seed_visitors_data())


# ==================== 公告功能 ====================

@features_bp.route('/api/announcements', methods=['GET'])
@login_required
def get_announcements():
    """获取最新公告列表"""
    announcements = Announcement.query.filter_by(is_active=True).order_by(
        Announcement.created_at.desc()
    ).limit(10).all()

    return jsonify({
        'success': True,
        'announcements': [a.to_dict() for a in announcements]
    })


@features_bp.route('/api/announcement/latest', methods=['GET'])
@login_required
def get_latest_announcement():
    """获取最新一条公告（用于首页弹窗）"""
    announcement = Announcement.query.filter_by(is_active=True).order_by(
        Announcement.created_at.desc()
    ).first()

    if announcement:
        return jsonify({
            'success': True,
            'announcement': announcement.to_dict()
        })
    else:
        return jsonify({
            'success': True,
            'announcement': None
        })
