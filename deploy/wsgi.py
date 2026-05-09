#!/usr/bin/env python3
"""
寻尤APP - PythonAnywhere WSGI入口文件
将此文件放在 /var/www/你的用户名_pythonanywhere_com_wsgi.py
"""

import os
import sys

# ====== 配置区域 - 根据你的实际情况修改 ======
PROJECT_DIR = '/home/你的用户名/xunyou-app'  # 改成你的PythonAnywhere用户名
# ============================================

# 将项目目录添加到Python路径
sys.path.insert(0, PROJECT_DIR)

# 切换工作目录到项目根目录
os.chdir(PROJECT_DIR)

# 确保instance目录存在
os.makedirs(os.path.join(PROJECT_DIR, 'instance'), exist_ok=True)
os.makedirs(os.path.join(PROJECT_DIR, 'static', 'uploads', 'avatars'), exist_ok=True)
os.makedirs(os.path.join(PROJECT_DIR, 'static', 'uploads', 'posts'), exist_ok=True)

# 导入Flask应用
from app import app as application, db, init_seed_data

# 初始化数据库
with application.app_context():
    db.create_all()
    # 首次部署时初始化种子数据
    try:
        from models import User
        if User.query.count() == 0:
            print("首次部署，初始化种子数据...")
            init_seed_data()
    except Exception as e:
        print(f"初始化种子数据失败: {e}")

# PythonAnywhere使用WSGI，不需要SocketIO的run
# SocketIO会自动降级为polling模式
