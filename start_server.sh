#!/bin/bash

# 设置环境变量
export APP_ENV=PROD

# 检查是否有正在运行的 gunicorn 服务
PIDS=$(pgrep -f 'runserver:app')

if [ -n "$PIDS" ]; then
    echo "Found existing gunicorn processes with PIDs: $PIDS. Terminating..."
    # 杀掉这些进程
    kill -9 $PIDS
    if [ $? -eq 0 ]; then
        echo "Existing gunicorn processes terminated successfully."
    else
        echo "Failed to terminate existing gunicorn processes."
        exit 1
    fi
else
    echo "No existing gunicorn processes found."
fi

# 启动 gunicorn 服务器
./venv/bin/gunicorn --worker-class=gthread --log-level debug -w 1 --threads 10 --timeout 120 -b 0.0.0.0:9999 runserver:app -D --access-logfile /root/work/chatgpt-wecom/logs/access.log --error-logfile /root/work/chatgpt-wecom/logs/error.log

# 检查是否启动成功，并给予提示
if [ $? -eq 0 ]; then
    echo "Server started successfully"
else
    echo "Failed to start the server"
fi
