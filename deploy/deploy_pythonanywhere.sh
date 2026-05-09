#!/bin/bash
# ============================================================
# 寻尤APP - PythonAnywhere 一键部署脚本
# 
# 使用方法：
# 1. 注册一个新的PythonAnywhere账号（推荐，免费版只能1个web app）
# 2. 打开 Bash Console（https://www.pythonanywhere.com/user/你的用户名/consoles/bash/）
# 3. 粘贴运行: bash <(curl -sL https://raw.githubusercontent.com/pwy1230/xunyou-app/main/deploy/deploy_pythonanywhere.sh)
#    或者先clone再运行
# ============================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  寻尤APP - PythonAnywhere 部署脚本${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# 获取当前用户名（PythonAnywhere的用户名就是系统用户名）
PA_USER=$(whoami)
echo -e "${GREEN}当前PythonAnywhere用户: ${PA_USER}${NC}"

# 项目目录
PROJECT_DIR="/home/${PA_USER}/xunyou-app"
VENV_DIR="/home/${PA_USER}/.virtualenvs/xunyou"

echo ""
echo -e "${YELLOW}步骤 1/6: 克隆代码...${NC}"
if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}项目目录已存在，拉取最新代码...${NC}"
    cd "$PROJECT_DIR"
    git pull origin main
else
    git clone https://github.com/pwy1230/xunyou-app.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

echo ""
echo -e "${YELLOW}步骤 2/6: 创建Python虚拟环境...${NC}"
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}虚拟环境已存在，跳过创建${NC}"
else
    python3 -m venv "$VENV_DIR"
fi

echo ""
echo -e "${YELLOW}步骤 3/6: 安装Python依赖...${NC}"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo ""
echo -e "${YELLOW}步骤 4/6: 配置WSGI入口文件...${NC}"

# 创建WSGI文件
WSGI_FILE="/var/www/${PA_USER}_pythonanywhere_com_wsgi.py"
cat > "$WSGI_FILE" << WSGI_EOF
import os
import sys

# 项目目录
PROJECT_DIR = '/home/${PA_USER}/xunyou-app'
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

# 确保必要目录存在
os.makedirs(os.path.join(PROJECT_DIR, 'instance'), exist_ok=True)
os.makedirs(os.path.join(PROJECT_DIR, 'static', 'uploads', 'avatars'), exist_ok=True)
os.makedirs(os.path.join(PROJECT_DIR, 'static', 'uploads', 'posts'), exist_ok=True)

# 设置环境变量
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
        print(f"数据库初始化注意: {e}")
WSGI_EOF

echo -e "${GREEN}WSGI文件已创建: ${WSGI_FILE}${NC}"

echo ""
echo -e "${YELLOW}步骤 5/6: 配置PythonAnywhere Web App...${NC}"
echo ""
echo -e "${RED}⚠️  以下步骤需要手动操作（API无法创建Web App）：${NC}"
echo ""
echo -e "1. 打开 ${BLUE}https://www.pythonanywhere.com/web_app_setup/${NC}"
echo -e "2. 点击 ${GREEN}'Add a new web app'${NC}"
echo -e "3. 选择域名: ${PA_USER}.pythonanywhere.com"
echo -e "4. 选择 ${GREEN}'Manual configuration'${NC}（手动配置）"
echo -e "5. 选择 Python 版本: ${GREEN}Python 3.10${NC}（或最新可用版本）"
echo -e "6. 设置虚拟环境路径: ${GREEN}${VENV_DIR}${NC}"
echo -e "7. 确认WSGI文件路径: ${GREEN}${WSGI_FILE}${NC}"
echo ""

echo -e "${YELLOW}步骤 6/6: 设置静态文件映射...${NC}"
echo ""
echo -e "${RED}⚠️  需要在Web App设置页面手动添加静态文件映射：${NC}"
echo ""
echo -e "  URL: ${GREEN}/static/${NC}  ->  Directory: ${GREEN}${PROJECT_DIR}/static/${NC}"
echo ""

echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}✅ 代码部署完成！${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "访问地址: ${GREEN}https://${PA_USER}.pythonanywhere.com${NC}"
echo ""
echo -e "${YELLOW}注意事项：${NC}"
echo -e "1. PythonAnywhere免费版不支持WebSocket，SocketIO会降级为polling模式"
echo -e "2. 免费版每天CPU秒数有限，访问量大会触发限制"
echo -e "3. 免费版3个月不登录会被清理，请定期登录"
echo -e "4. 如需更新代码: cd ${PROJECT_DIR} && git pull"
echo -e "5. 更新后需Reload Web App（在Web页面点Reload按钮）"
echo ""
echo -e "${YELLOW}测试账号：${NC}"
echo -e "  管理员: 13800138000 / admin123"
echo -e "  用户:   13800138001~23 / 123456"
