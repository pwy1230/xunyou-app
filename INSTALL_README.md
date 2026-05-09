# 闫雨浪新功能安装指南

## 已创建的文件

1. **features_bp.py** - 新功能 Blueprint（签到、访客、公告API）
2. **sensitive_filter.py** - 敏感词过滤模块（DFA算法）
3. **install_features.py** - 安装脚本

## 安装步骤

### 方法一：运行安装脚本（推荐）

```
cd C:\Users\Administrator\Desktop\闫雨浪
python install_features.py
```

脚本会自动完成：
- ✅ 备份原文件（*.bak）
- ✅ 添加新数据库模型（Announcement、SensitiveWord、SignInLog）
- ✅ 注册 features_bp Blueprint
- ✅ 添加敏感词过滤到 chat.py
- ✅ 修改前端页面（home.html、messages.html、wallet.html、profile.html）
- ✅ 初始化数据库表
- ✅ 初始化敏感词库（约40个）
- ✅ 创建默认公告

### 方法二：手动修改

如果安装脚本执行失败，请手动执行以下步骤：

#### 1. 修改 models.py（末尾添加）
```python
class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SensitiveWord(db.Model):
    __tablename__ = 'sensitive_words'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(200), unique=True, nullable=False)
    category = db.Column(db.String(50), default='other')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SignInLog(db.Model):
    __tablename__ = 'signin_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    coins_earned = db.Column(db.Integer, default=5)
    consecutive_days = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### 2. 修改 app.py（import区域添加）
```python
from features_bp import features_bp
```

#### 3. 修改 app.py（Blueprint注册区域添加）
```python
app.register_blueprint(features_bp)
```

#### 4. 修改 chat.py（send_message函数开头添加）
```python
from sensitive_filter import check_content
# 在 sender = User.query.get(sender_id) 之前添加
if msg_type == 'text':
    is_sensitive, filtered_word = check_content(content)
    if is_sensitive:
        return False, "内容包含违规信息，无法发送", None
```

## 新增功能说明

### 1. 体验优化

| 功能 | 说明 |
|------|------|
| 距离显示 | 用户列表显示"800m"而不是城市名 |
| 女号"刚刚在线" | 女性用户永远显示"1分钟前在线" |
| 消息红点 | 底部消息图标永远显示红点 |
| 限时优惠倒计时 | wallet页面显示倒计时（实际不过期） |

### 2. 功能类

| 功能 | 说明 |
|------|------|
| 每日签到 | 每天签到领5金币，7天连续35金币 |
| 谁看过我 | 注册后自动生成3-5条虚拟访客 |
| 敏感词屏蔽 | DFA算法过滤聊天内容 |

### 3. 管理后台

新增3个Tab：
- **举报** - 查看和处理用户举报
- **公告** - 发布和管理系统公告
- **敏感词** - 管理敏感词库

## 启动应用

安装完成后重启Flask：
```
python app.py
```

## 验证安装

访问 http://172.16.10.17:5000 ，用管理员账号登录：
- 手机号：13800138004
- 密码：admin123

在后台可以看到新增的"举报"、"公告"、"敏感词"Tab。

## 回滚方法

如果安装失败，运行以下命令恢复备份：
```
copy app.py.bak app.py
copy models.py.bak models.py
copy chat.py.bak chat.py
copy templates\home.html.bak templates\home.html
copy templates\messages.html.bak templates\messages.html
copy templates\wallet.html.bak templates\wallet.html
copy templates\profile.html.bak templates\profile.html
```
