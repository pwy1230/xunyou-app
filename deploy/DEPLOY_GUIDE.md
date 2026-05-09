# 寻尤APP 部署指南

## 概述

将寻尤APP从本地部署到PythonAnywhere云平台，实现公网访问，并打包WebView APK。

---

## 方案选择

### 为什么新建PythonAnywhere账号？

PythonAnywhere免费版只允许**1个Web App**。你现有的 `pwy` 账号已经跑了video-dispatch。

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A. 新建账号（推荐）** | 简单干净，互不影响 | 需要注册新账号 |
| B. Blueprint子路径 | 不用新账号 | 两个APP耦合，修改复杂 |
| C. 其他云服务 | 选择多 | 学习成本高 |

**推荐方案A**：注册一个新PythonAnywhere账号（如 `xunyou`），域名就是 `xunyou.pythonanywhere.com`。

---

## 步骤1：注册新PythonAnywhere账号

1. 访问 https://www.pythonanywhere.com/registration/
2. 注册新账号，用户名建议：`xunyou` 或 `xunyouapp`（会变成域名）
3. 选择 **Beginner plan**（免费）
4. 验证邮箱

---

## 步骤2：运行一键部署脚本

注册完成后，打开Bash Console：

1. 登录新账号
2. 点击 **Consoles** → **Bash**
3. 运行部署脚本：

```bash
# 方法1：直接运行（需要先push代码到GitHub公开仓库或设置token）
git clone https://github.com/pwy1230/xunyou-app.git ~/xunyou-app
cd ~/xunyou-app
bash deploy/deploy_pythonanywhere.sh
```

或者手动操作（见下方详细步骤）。

---

## 步骤3：手动部署（详细版）

如果一键脚本有问题，按以下步骤手动操作：

### 3.1 克隆代码

```bash
cd ~
git clone https://github.com/pwy1230/xunyou-app.git
cd xunyou-app
```

### 3.2 创建虚拟环境

```bash
python3 -m venv ~/.virtualenvs/xunyou
source ~/.virtualenvs/xunyou/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

### 3.3 创建Web App

1. 回到PythonAnywhere首页，点击 **Web** 标签
2. 点击 **Add a new web app**
3. 确认域名（如 `xunyou.pythonanywhere.com`）
4. 选择 **Manual configuration**（不要选Flask模板，那个会配置错）
5. 选择 **Python 3.10**（或最新版本）

### 3.4 配置Web App

在Web App配置页面：

**Virtualenv 路径**：
```
/home/你的用户名/.virtualenvs/xunyou
```

**WSGI配置文件** - 点击WSGI文件链接，替换内容为：

```python
import os
import sys

# ====== 修改为你的用户名 ======
USERNAME = '你的用户名'  # 如 xunyou
# ==============================

PROJECT_DIR = f'/home/{USERNAME}/xunyou-app'
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

# 确保目录存在
os.makedirs(os.path.join(PROJECT_DIR, 'instance'), exist_ok=True)
os.makedirs(os.path.join(PROJECT_DIR, 'static', 'uploads', 'avatars'), exist_ok=True)
os.makedirs(os.path.join(PROJECT_DIR, 'static', 'uploads', 'posts'), exist_ok=True)

# 环境变量
os.environ['DATABASE_PATH'] = os.path.join(PROJECT_DIR, 'yan_yu_lang.db')
os.environ['UPLOAD_FOLDER'] = os.path.join(PROJECT_DIR, 'static', 'uploads')

# 导入Flask应用
from app import app as application, db

# 初始化数据库
with application.app_context():
    db.create_all()
    try:
        from models import User
        if User.query.count() == 0:
            print("首次部署，初始化种子数据...")
            from app import init_db
            init_db()
    except Exception as e:
        print(f"初始化注意: {e}")
```

**静态文件映射** - 在 "Static files" 部分：

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/你的用户名/xunyou-app/static` |

### 3.5 Reload Web App

点击页面顶部的绿色 **Reload** 按钮。

### 3.6 验证部署

打开浏览器访问：`https://你的用户名.pythonanywhere.com`

应该能看到寻尤APP的闪屏页面。

---

## PythonAnywhere限制说明

| 限制 | 免费版 | 付费版 |
|------|--------|--------|
| Web App数量 | 1个 | 多个 |
| 每日CPU秒数 | 100秒 | 更多 |
| 存储 | 512MB | 更多 |
| WebSocket | ❌ 不支持 | ✅ 支持 |
| 自定义域名 | ❌ | ✅ |
| HTTPS | ✅ | ✅ |

### SocketIO降级说明

免费版不支持WebSocket，SocketIO会自动降级为 **long-polling** 模式：
- 聊天功能正常，但消息可能有1-3秒延迟
- 实时在线状态更新会慢一些
- 不影响核心使用体验

---

## 步骤4：打包WebView APK

部署成功后，可以用WebView把网址包装成APP安装到安卓手机。

### 方法1：在线打包（最简单）

1. 访问 **GoNative.io**（https://gonative.io/）
2. 输入网址：`https://你的用户名.pythonanywhere.com`
3. 配置APP名称：寻尤
4. 下载APK

### 方法2：WebIntoApp（推荐）

1. 访问 https://www.webintoapp.com/
2. 输入URL：`https://你的用户名.pythonanywhere.com`
3. 设置APP名：寻尤
4. 选择图标
5. 生成并下载APK

### 方法3：Cordova本地打包

如果云电脑有Node.js环境，可以使用项目内提供的Cordova配置：

```bash
# 安装Cordova
npm install -g cordova

# 使用项目提供的配置
cd ~/xunyou-app/deploy/cordova
npm install
cordova platform add android
cordova build android
```

生成的APK在 `platforms/android/app/build/outputs/apk/debug/`

---

## 步骤5：更新部署

当代码更新后：

```bash
cd ~/xunyou-app
git pull origin main
```

然后到Web页面点 **Reload** 按钮。

---

## 故障排除

### 502 Bad Gateway
- 检查WSGI文件中的路径是否正确
- 检查虚拟环境中是否安装了所有依赖
- 查看错误日志：Web页面 → Log files → Server log

### 静态文件404
- 检查静态文件映射配置是否正确
- URL末尾要有 `/`：`/static/`
- Directory路径要绝对路径

### 数据库错误
- 确认 `instance/` 目录存在且有写权限
- 检查 DATABASE_PATH 环境变量

### 上传文件失败
- 确认 `static/uploads/` 目录有写权限
- 免费版存储限制512MB

---

## 测试账号

| 角色 | 手机号 | 密码 |
|------|--------|------|
| 管理员 | 13800138000 | admin123 |
| 测试用户 | 13800138001~23 | 123456 |
| 测试男用户 | 13800138004 | 123456 |
