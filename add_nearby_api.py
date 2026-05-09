# -*- coding: utf-8 -*-
"""
add_nearby_api.py
修改app.py添加/api/nearby路由，修改/home路由传online_users
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, 'app.py'), 'r', encoding='utf-8') as f:
    app_content = f.read()

# 检查是否已经添加过
if '/api/nearby' not in app_content:
    # ==================== 1. 修改 /home 路由 ====================
    print("步骤1: 修改 /home 路由...")
    
    old_home = '''@app.route('/home')
@login_required
def home():
    # 直接后端查询用户列表，传给模板渲染
    target_gender = 'female' if current_user.gender == 'male' else 'male'
    users = User.query.filter_by(gender=target_gender).filter(User.id != current_user.id).order_by(User.is_online.desc(), User.last_active.desc()).limit(30).all()
    user_list = []
    for u in users:
        d = u.to_dict()
        d['tags'] = ['真诚', '有趣'] if u.is_online else ['神秘', '待发现']
        user_list.append(d)
    return render_template('home.html', recommend_users=user_list)'''
    
    new_home = '''@app.route('/home')
@login_required
def home():
    # 直接后端查询用户列表，传给模板渲染
    target_gender = 'female' if current_user.gender == 'male' else 'male'
    users = User.query.filter_by(gender=target_gender).filter(User.id != current_user.id).order_by(User.is_online.desc(), User.last_active.desc()).limit(30).all()
    user_list = []
    for u in users:
        d = u.to_dict()
        d['tags'] = ['真诚', '有趣'] if u.is_online else ['神秘', '待发现']
        user_list.append(d)
    
    # 获取在线用户列表（最多10个）
    online_users = User.query.filter_by(is_online=True).filter(User.id != current_user.id).limit(10).all()
    online_list = [u.to_dict() for u in online_users]
    
    return render_template('home.html', recommend_users=user_list, online_users=online_list)'''
    
    app_content = app_content.replace(old_home, new_home)
    print("✓ /home 路由已修改，添加 online_users 参数")
    
    # ==================== 2. 添加 /api/nearby 路由 ====================
    print("\n步骤2: 添加 /api/nearby 路由...")
    
    # 找到合适的位置插入新路由（在 # --- 首页推荐 --- 注释后）
    insert_marker = "# --- 首页推荐 ---"
    if insert_marker in app_content:
        new_api = '''

@app.route('/api/nearby')
@login_required
def api_nearby():
    """获取附近用户列表"""
    if not current_user.is_vip:
        return jsonify({'success': False, 'need_vip': True, 'message': '需要诚意会员'})
    
    target_gender = 'female' if current_user.gender == 'male' else 'male'
    users = User.query.filter_by(gender=target_gender).filter(User.id != current_user.id).all()
    
    result = []
    for u in users:
        d = u.to_dict()
        import random
        d['distance'] = round(random.uniform(0.3, 15.0), 1)
        result.append(d)
    
    result.sort(key=lambda x: x['distance'])
    return jsonify({'success': True, 'users': result})

'''
        app_content = app_content.replace(insert_marker, new_api + insert_marker)
        print("✓ /api/nearby 路由已添加")
    else:
        # 备用位置：找到 api_recommendations 之后
        insert_marker2 = "@app.route('/api/recommendations')"
        if insert_marker2 in app_content:
            # 在它之前插入
            new_api = '''

@app.route('/api/nearby')
@login_required
def api_nearby():
    """获取附近用户列表"""
    if not current_user.is_vip:
        return jsonify({'success': False, 'need_vip': True, 'message': '需要诚意会员'})
    
    target_gender = 'female' if current_user.gender == 'male' else 'male'
    users = User.query.filter_by(gender=target_gender).filter(User.id != current_user.id).all()
    
    result = []
    for u in users:
        d = u.to_dict()
        import random
        d['distance'] = round(random.uniform(0.3, 15.0), 1)
        result.append(d)
    
    result.sort(key=lambda x: x['distance'])
    return jsonify({'success': True, 'users': result})

'''
            app_content = app_content.replace(insert_marker2, new_api + insert_marker2)
            print("✓ /api/nearby 路由已添加")

    # 保存修改后的文件
    with open(os.path.join(BASE, 'app.py'), 'w', encoding='utf-8') as f:
        f.write(app_content)
    
    print("\n✅ add_nearby_api.py 执行完成！")
    print("✓ app.py 已修改")
    print("  - /home 路由现在传递 online_users 参数")
    print("  - 新增 /api/nearby API：")
    print("    - 需要登录且是VIP")
    print("    - 返回附近用户列表（含模拟距离）")
    print("    - 非VIP返回 need_vip: True")

else:
    print("✓ /api/nearby 路由已存在，跳过")
    print("\n✅ add_nearby_api.py 执行完成！")
