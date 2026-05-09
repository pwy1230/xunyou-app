# -*- coding: utf-8 -*-
"""seed_data.py - 给闫雨浪灌入20-30个假用户+动态+访客数据"""
import os
import sys
import random
import json

# 使用相对路径
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)

# 国内可用的占位图函数
def placeholder_image(width=200, height=200, bg='ff6b9d', text='Photo'):
    """生成本地占位图URL（通过Flask路由返回SVG）"""
    return f'/api/placeholder/{width}/{height}/{bg}?t={text}'

# 女生名字池
FEMALE_NAMES = [
    '小雨', '甜甜', '梦梦', '小可爱', '糖果', '小鹿', '棉花糖', '奶茶',
    '蜜桃', '樱桃', '小糯米', '芒果', '柠檬', '草莓', '蓝莓', '小星星',
    '云朵', '花花', '泡泡', '小兔子', '饼干', '巧克力', '冰淇淋', '小棉袄',
    '椰果', '布丁', '奶盖', '芋圆', '珍珠'
]

# 个性签名池
BIOS = [
    '在成都，想认识有趣的人~', '努力变优秀中💪', '喜欢旅游拍照✈️',
    '一个人的时候看看书📖', '吃货一枚，成都美食走起🍜', '瑜伽爱好者🧘‍♀️',
    '猫奴，养了两只橘猫🐱', '跑步打卡第100天🏃‍♀️', '追剧ing，最近在看…',
    '周末喜欢逛展🎨', '听音乐发呆最舒服🎧', '大学刚毕业，来交个朋友',
    '喜欢深夜撸串🍺', '健身第三年，坚持就是胜利', '摄影小白，多指教📷',
    '在找志同道合的人', '火锅底料了解一下🍲', '喜欢猫猫狗狗一切毛茸茸',
    '每天都是元气满满的一天☀️', '认真生活，慢慢相遇',
    '喜欢看日落的人🌅', '在准备考研，偶尔摸鱼', '运动使我快乐🎾',
    '热爱生活的打工人', '周末去哪玩？', '永远年轻永远热泪盈眶',
    '只想和有趣的人聊天', '减脂中…但好想吃炸鸡🍗', '梦想是环游世界🌍'
]

# 兴趣标签池
TAGS_POOL = [
    '旅行', '美食', '摄影', '健身', '瑜伽', '跑步', '追剧',
    '音乐', '读书', '画画', '猫奴', '狗奴', '游戏', '电影',
    '穿搭', '化妆', '手工', '烹饪', '游泳', '骑行', '露营',
    '咖啡', '奶茶', '逛街', '追星', '动漫', '篮球', '滑雪'
]

# 城市池
CITIES = ['成都', '成都', '成都', '成都', '成都', '重庆', '绵阳', '德阳', '乐山', '宜宾']

# 动态内容池
POST_CONTENTS = [
    '今天天气真好，出去走走~ ☀️',
    '刚吃了超好吃的火锅，推荐！🍲',
    '周末去了公园，拍了好多花🌸',
    '健身打卡！今天练了腿💀',
    '分享一张今天的OOTD ✨',
    '猫咪又在键盘上踩来踩去了🐱',
    '新买的奶茶好好喝🧋',
    '下班了，终于可以追剧了🎬',
    '今天读了本书，推荐给大家📖',
    '做了个蛋糕，虽然有点丑但是很好吃🎂',
    '去了新开的咖啡馆，环境超好☕',
    '晨跑5公里，感觉整个人都清醒了🏃‍♀️',
    '雨天的成都也很美🌧️',
    '周末市集逛了一圈，买了很多小玩意🛍️',
    '今天的晚霞绝了🌅',
    '终于学会了做寿司🍣',
    '和闺蜜逛街的一天🛒',
    '春熙路的人也太多了吧😂',
    '分享一下今天的早餐🥐',
    '加班到9点，但是项目终于上线了💪',
    '今天的OOTD，有点小开心😊',
    '周末宅家看电影，太舒服了🎥',
    '新学的舞蹈动作，记录一下💃',
    '今日份的美食打卡📸',
    '雨天窝在家里，听着雨声发呆🌧️',
    '今天收到礼物啦，好开心🎁',
    '健身房挥汗如雨，感觉自己棒棒的💪',
    '周末约了朋友吃饭聊天，开心🥳',
    '今天的夕阳真美，忍不住拍了几张📷',
    '终于等到周末，可以睡个懒觉啦🛏️'
]


def main(app=None):
    if app is None:
        from app import app
    from models import db, User, Post, Visitor, Comment, PostLike

    with app.app_context():
        # 1. 添加女用户
        existing_phones = set(u.phone for u in User.query.all())
        existing_count = User.query.filter_by(gender='female').count()
        need_count = 25 - existing_count  # 目标25个女号

        if need_count <= 0:
            print(f'已有 {existing_count} 个女号，无需添加')
        else:
            print(f'需要添加 {need_count} 个女号...')
            random.shuffle(FEMALE_NAMES)
            random.shuffle(BIOS)

            new_users = []
            for i in range(need_count):
                phone = f'13900{50000 + i}'
                if phone in existing_phones:
                    continue

                name = FEMALE_NAMES[i % len(FEMALE_NAMES)]
                bio = BIOS[i % len(BIOS)]
                tags = random.sample(TAGS_POOL, random.randint(2, 5))
                city = random.choice(CITIES)
                age = random.randint(19, 28)
                # 头像使用国内可用的占位图
                avatar_idx = (existing_count + i) % 3 + 1
                colors = ['ff6b9d', 'c44dff', '4facfe']
                avatar = placeholder_image(200, 200, colors[(existing_count + i) % 3], name[:2] if len(name) >= 2 else name)

                user = User(
                    phone=phone,
                    gender='female',
                    nickname=name,
                    avatar=avatar,
                    age=age,
                    city=city,
                    bio=bio,
                    interest_tags=json.dumps(tags, ensure_ascii=False),
                    chat_price=random.choice([1.0, 2.0, 3.0, 5.0]),
                    coin_balance=random.randint(50, 500),
                    is_online=True,
                    last_active=None,
                    # 新增字段
                    height=random.choice([158, 160, 162, 163, 165, 167, 168, 170, 172]),
                    occupation=random.choice(['大学生', '模特', '主播', '白领', '教师', '护士', '设计师', '空姐', '健身教练', '网红']),
                    looking_for=random.choice(['有趣的灵魂', '暖男', '聊得来的人', '真心的朋友', '一起旅游的人', '成熟稳重', '阳光帅气']),
                )
                user.set_password('123456')
                # 设置照片墙（3-6张随机图片）- 使用国内可用的占位图
                num_photos = random.randint(3, 6)
                photo_urls = [placeholder_image(400, 500, random.choice(['ff6b9d', 'c44dff', '4facfe']), f'P{i+1}') for i in range(num_photos)]
                user.set_photos(photo_urls)
                db.session.add(user)
                new_users.append(user)

            db.session.commit()
            print(f'已添加 {len(new_users)} 个女号')

        # 2. 添加动态
        all_females = User.query.filter_by(gender='female').all()
        existing_posts = Post.query.count()
        need_posts = 30 - existing_posts  # 目标30条动态

        if need_posts <= 0:
            print(f'已有 {existing_posts} 条动态，无需添加')
        else:
            print(f'需要添加 {need_posts} 条动态...')
            for i in range(need_posts):
                author = random.choice(all_females)
                content = random.choice(POST_CONTENTS)
                # 随机生成1-3张图片（保留20%纯文字）- 使用国内可用的占位图
                num_images = random.choice([0, 0, 1, 1, 2, 3])
                image_paths = [placeholder_image(400, 400, random.choice(['ff6b9d', 'c44dff', '4facfe']), f'IMG{i+1}') for i in range(num_images)]
                post = Post(
                    user_id=author.id,
                    content=content,
                    like_count=random.randint(2, 88),
                    comment_count=random.randint(0, 15),
                    is_visible=True
                )
                if image_paths:
                    post.set_images(image_paths)
                db.session.add(post)
            db.session.commit()
            print(f'已添加 {need_posts} 条动态')

        # 3. 给测试男号添加访客记录
        test_male = User.query.filter_by(phone='13800138004').first()
        if test_male:
            existing_visitors = Visitor.query.filter_by(visited_id=test_male.id).count()
            if existing_visitors < 5:
                # 添加3-5个访客
                visitors_to_add = random.sample(all_females, min(5, len(all_females)))
                for v in visitors_to_add:
                    exists = Visitor.query.filter_by(visitor_id=v.id, visited_id=test_male.id).first()
                    if not exists:
                        visitor = Visitor(
                            visitor_id=v.id,
                            visited_id=test_male.id
                        )
                        db.session.add(visitor)
                db.session.commit()
                print(f'已为测试男号添加访客记录')

        # 4. 统计
        total_users = User.query.count()
        total_females = User.query.filter_by(gender='female').count()
        total_posts = Post.query.count()
        print(f'')
        print(f'========== 数据统计 ==========')
        print(f'总用户数: {total_users}')
        print(f'女号数: {total_females}')
        print(f'动态数: {total_posts}')
        print(f'===============================')
        print(f'')
        print(f'完成！重启 Flask 后刷新手机即可看到更多用户和动态')


if __name__ == '__main__':
    main()
