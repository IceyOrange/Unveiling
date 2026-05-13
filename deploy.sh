#!/bin/bash
# Unveiling 演示部署脚本（阿里云香港轻量服务器 / Ubuntu 22.04）
# 使用方式：scp 到服务器后执行 ./deploy.sh

set -e

APP_DIR="/opt/unveiling"
REPO_URL=""

echo "=== Unveiling 部署脚本 ==="

# 1. 安装依赖
echo "[1/6] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 python3-venv python3-pip nginx

# 2. 创建目录
echo "[2/6] 创建应用目录..."
sudo mkdir -p "$APP_DIR"
sudo chown "$USER:$USER" "$APP_DIR"

# 3. 克隆代码（如果没有）
echo "[3/6] 拉取代码..."
if [ ! -d "$APP_DIR/.git" ]; then
    if [ -z "$REPO_URL" ]; then
        echo "错误：请先将代码 push 到 GitHub，然后修改 REPO_URL 变量"
        exit 1
    fi
    git clone "$REPO_URL" "$APP_DIR"
else
    cd "$APP_DIR"
    git pull
fi

cd "$APP_DIR"

# 4. 创建虚拟环境并安装依赖
echo "[4/6] 安装 Python 依赖..."
python3 -m venv .venv --clear
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet gunicorn gevent

# 5. 写入环境变量模板（用户需要手动编辑）
if [ ! -f ".env" ]; then
    echo "[5/6] 创建环境变量文件..."
    cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-deepseek-key-here
OPENAI_API_BASE=https://api.deepseek.com/v1
OPENAI_MODEL_NAME=deepseek-chat
SERPER_API_KEY=your-serper-key-here
EOF
    echo "⚠️  请编辑 $APP_DIR/.env 文件，填入你的真实 API Key"
else
    echo "[5/6] .env 文件已存在，跳过"
fi

# 6. 配置 systemd 服务
echo "[6/6] 配置系统服务..."
sudo tee /etc/systemd/system/unveiling.service > /dev/null << EOF
[Unit]
Description=Unveiling Demo Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/.venv/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/gunicorn -k gevent -w 1 -b 0.0.0.0:8000 --timeout 300 --access-logfile - frontend.app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable unveiling

echo ""
echo "=== 部署完成 ==="
echo ""
echo "下一步："
echo "  1. 编辑环境变量：vim $APP_DIR/.env"
echo "  2. 启动服务：sudo systemctl start unveiling"
echo "  3. 查看状态：sudo systemctl status unveiling"
echo "  4. 查看日志：sudo journalctl -u unveiling -f"
echo ""
echo "访问地址：http://$(curl -s ifconfig.me):8000"
echo ""
echo "如果需要 80 端口访问，可以运行：sudo python3 -m http.server 80 &"
