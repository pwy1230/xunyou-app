"""
金币系统模块
"""
from models import db, User, Transaction
from datetime import datetime

# 平台抽成比例
PLATFORM_FEE_RATE = 0.30  # 30%平台抽成

# 充值档位 (元 -> 金币)
RECHARGE_PACKAGES = [
    {'id': 1, 'name': '小试牛刀', 'yuan': 6, 'coins': 60, 'bonus': 0},
    {'id': 2, 'name': '渐入佳境', 'yuan': 30, 'coins': 300, 'bonus': 15},
    {'id': 3, 'name': '乐在其中', 'yuan': 68, 'coins': 680, 'bonus': 68},
    {'id': 4, 'name': '尊贵会员', 'yuan': 198, 'coins': 1980, 'bonus': 396},
]

# 提现设置
MIN_WITHDRAW_AMOUNT = 50  # 最低提现金额（元）
WITHDRAW_FEE_RATE = 0.10  # 提现手续费 10%


def recharge_coins(user_id, package_id):
    """
    模拟充值金币
    :param user_id: 用户ID
    :param package_id: 充值套餐ID
    :return: (success, message, coins_added)
    """
    package = next((p for p in RECHARGE_PACKAGES if p['id'] == package_id), None)
    if not package:
        return False, "充值套餐不存在", 0
    
    user = User.query.get(user_id)
    if not user:
        return False, "用户不存在", 0
    
    total_coins = package['coins'] + package['bonus']
    user.coin_balance += total_coins
    
    # 记录交易
    transaction = Transaction(
        user_id=user_id,
        type='recharge',
        amount=total_coins,
        balance_after=user.coin_balance,
        description=f"充值 {package['name']}，获得 {total_coins} 金币"
    )
    db.session.add(transaction)
    db.session.commit()
    
    return True, f"充值成功，获得 {total_coins} 金币", total_coins


def consume_coins(sender_id, receiver_id, amount):
    """
    消费金币（男用户发消息扣费）
    :param sender_id: 发送方（男用户）
    :param receiver_id: 接收方（女用户）
    :return: (success, message)
    """
    sender = User.query.get(sender_id)
    if not sender:
        return False, "发送用户不存在"
    
    if sender.coin_balance < amount:
        return False, "余额不足"
    
    # 扣费
    sender.coin_balance -= amount
    
    # 记录交易
    transaction = Transaction(
        user_id=sender_id,
        type='consume',
        amount=-amount,
        balance_after=sender.coin_balance,
        description=f"发送消息消费 {amount} 金币"
    )
    db.session.add(transaction)
    db.session.commit()
    
    return True, "消费成功"


def calculate_income(chat_price):
    """
    计算女用户收到消息后的实际收入
    :param chat_price: 聊天价格
    :return: (user_gets, platform_fee)
    """
    platform_fee = chat_price * PLATFORM_FEE_RATE
    user_gets = chat_price - platform_fee
    return user_gets, platform_fee


def add_income(user_id, amount, platform_fee, sender_id):
    """
    女用户获得收入
    :param user_id: 女用户ID
    :param amount: 实际获得的金币
    :param platform_fee: 平台抽成
    :param sender_id: 发送者ID（用于描述）
    """
    user = User.query.get(user_id)
    if not user:
        return False, "用户不存在"
    
    user.coin_balance += amount
    
    # 记录交易
    transaction = Transaction(
        user_id=user_id,
        type='income',
        amount=amount,
        balance_after=user.coin_balance,
        description=f"消息收益，获得 {amount} 金币（平台抽成 {platform_fee}）"
    )
    db.session.add(transaction)
    db.session.commit()
    
    return True, "收入到账"


def withdraw_coins(user_id, yuan_amount):
    """
    模拟提现
    :param user_id: 用户ID
    :param yuan_amount: 提现金额（元）
    :return: (success, message, actual_amount)
    """
    if yuan_amount < MIN_WITHDRAW_AMOUNT:
        return False, f"最低提现金额为 {MIN_WITHDRAW_AMOUNT} 元", 0
    
    # 转换：金币 -> 元（1元=10金币）
    coin_amount = yuan_amount * 10
    
    user = User.query.get(user_id)
    if not user:
        return False, "用户不存在", 0
    
    if user.coin_balance < coin_amount:
        return False, "金币余额不足", 0
    
    # 计算实际到账金额（扣除手续费）
    fee = coin_amount * WITHDRAW_FEE_RATE
    actual_coins = coin_amount - fee
    
    # 扣款
    user.coin_balance -= coin_amount
    
    # 记录交易
    transaction = Transaction(
        user_id=user_id,
        type='withdraw',
        amount=-coin_amount,
        balance_after=user.coin_balance,
        description=f"提现 {yuan_amount} 元，手续费 {fee/10} 元，实际到账 {actual_coins/10} 元"
    )
    db.session.add(transaction)
    db.session.commit()
    
    return True, f"提现申请已提交，预计1-3个工作日到账", actual_coins


def get_transaction_history(user_id, limit=50):
    """
    获取交易记录
    """
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(
        Transaction.created_at.desc()
    ).limit(limit).all()
    return [t.to_dict() for t in transactions]


def get_user_stats(user_id):
    """
    获取用户统计信息
    """
    user = User.query.get(user_id)
    if not user:
        return None
    
    # 发送的消息数
    sent_count = Message.query.filter_by(sender_id=user_id).count()
    
    # 收到的消息数
    received_count = Message.query.filter_by(receiver_id=user_id).count()
    
    # 总收入/支出
    total_income = sum([t.amount for t in Transaction.query.filter_by(user_id=user_id, type='income').all()])
    total_consume = sum([abs(t.amount) for t in Transaction.query.filter_by(user_id=user_id, type='consume').all()])
    total_recharge = sum([t.amount for t in Transaction.query.filter_by(user_id=user_id, type='recharge').all()])
    
    return {
        'coin_balance': user.coin_balance,
        'sent_messages': sent_count,
        'received_messages': received_count,
        'total_income': total_income,
        'total_consume': total_consume,
        'total_recharge': total_recharge
    }


# 导入Message避免循环引用
from models import Message
