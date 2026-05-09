"""
聊天系统模块
"""
from models import db, User, Message, Visitor
from coin import consume_coins, calculate_income, add_income
from datetime import datetime
from flask_socketio import emit


def send_message(sender_id, receiver_id, content, msg_type='text'):
    """
    发送消息（包含付费逻辑）
    :param sender_id: 发送者ID
    :param receiver_id: 接收者ID
    :param content: 消息内容
    :param msg_type: 消息类型 text/image/emotion
    :return: (success, message, message_obj)
    """
    sender = User.query.get(sender_id)
    receiver = User.query.get(receiver_id)
    
    if not sender or not receiver:
        return False, "用户不存在", None
    
    # 检查是否被拉黑
    # TODO: 实现黑名单检查
    
    coin_cost = 0.0
    platform_fee = 0.0
    
    # 付费逻辑：男用户发给女用户需要扣费
    if sender.gender == 'male' and receiver.gender == 'female':
        chat_price = receiver.chat_price
        if chat_price <= 0:
            chat_price = 1.0
        
        # 检查余额
        if sender.coin_balance < chat_price:
            return False, "余额不足，请先充值", None
        
        # 扣费
        success, msg = consume_coins(sender_id, receiver_id, chat_price)
        if not success:
            return False, msg, None
        
        coin_cost = chat_price
        # 计算女用户收入
        user_gets, platform_fee = calculate_income(chat_price)
        # 女用户获得收入
        add_income(receiver_id, user_gets, platform_fee, sender_id)
    
    # 创建消息记录
    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        msg_type=msg_type,
        coin_cost=coin_cost,
        platform_fee=platform_fee
    )
    db.session.add(message)
    db.session.commit()
    
    return True, "发送成功", message


def get_chat_history(user1_id, user2_id, limit=50, offset=0):
    """
    获取聊天记录
    :param user1_id: 用户1ID
    :param user2_id: 用户2ID
    :param limit: 数量限制
    :param offset: 偏移量
    """
    messages = Message.query.filter(
        ((Message.sender_id == user1_id) & (Message.receiver_id == user2_id)) |
        ((Message.sender_id == user2_id) & (Message.receiver_id == user1_id))
    ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
    
    return [msg.to_dict() for msg in reversed(messages)]


def get_chat_list(user_id):
    """
    获取聊天列表（最近联系人）
    """
    # 获取所有与该用户有消息往来的用户ID
    sent_to = db.session.query(Message.receiver_id).filter(
        Message.sender_id == user_id
    ).distinct()
    
    received_from = db.session.query(Message.sender_id).filter(
        Message.receiver_id == user_id
    ).distinct()
    
    contact_ids = set([uid for uid, in sent_to.all()] + [uid for uid, in received_from.all()])
    
    chat_list = []
    for contact_id in contact_ids:
        contact = User.query.get(contact_id)
        if not contact:
            continue
        
        # 获取最新一条消息
        latest_msg = Message.query.filter(
            ((Message.sender_id == user_id) & (Message.receiver_id == contact_id)) |
            ((Message.sender_id == contact_id) & (Message.receiver_id == user_id))
        ).order_by(Message.created_at.desc()).first()
        
        # 获取未读消息数
        unread_count = Message.query.filter(
            Message.sender_id == contact_id,
            Message.receiver_id == user_id,
            Message.is_read == False
        ).count()
        
        chat_list.append({
            'user': contact.to_dict(),
            'latest_message': latest_msg.to_dict() if latest_msg else None,
            'unread_count': unread_count
        })
    
    # 按最新消息时间排序
    chat_list.sort(key=lambda x: x['latest_message']['created_at'] if x['latest_message'] else '', reverse=True)
    
    return chat_list


def mark_as_read(user_id, from_user_id):
    """
    标记消息为已读
    """
    Message.query.filter(
        Message.sender_id == from_user_id,
        Message.receiver_id == user_id,
        Message.is_read == False
    ).update({'is_read': True})
    db.session.commit()


def record_visitor(visitor_id, visited_id):
    """
    记录访客
    """
    if visitor_id == visited_id:
        return
    
    # 检查是否已记录
    existing = Visitor.query.filter_by(
        visitor_id=visitor_id,
        visited_id=visited_id
    ).first()
    
    if existing:
        existing.created_at = datetime.utcnow()
    else:
        visitor = Visitor(
            visitor_id=visitor_id,
            visited_id=visited_id
        )
        db.session.add(visitor)
    
    db.session.commit()


def get_visitors(user_id, limit=50):
    """
    获取访客列表
    """
    visitors = Visitor.query.filter_by(visited_id=user_id).order_by(
        Visitor.created_at.desc()
    ).limit(limit).all()
    
    return [{
        'visitor': v.visitor.to_dict() if v.visitor else None,
        'visited_at': v.created_at.isoformat() if v.created_at else None
    } for v in visitors]


def set_user_online(user_id, is_online=True):
    """
    设置用户在线状态
    """
    user = User.query.get(user_id)
    if user:
        user.is_online = is_online
        user.last_active = datetime.utcnow()
        db.session.commit()
