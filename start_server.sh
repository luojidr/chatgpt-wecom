#!/bin/bash

# 设置环境变量
export APP_ENV=DEV

# 检查是否有正在运行的 gunicorn 服务
PIDS=$(pgrep -f 'runserver:app')

if [ -n "$PIDS" ]; then
    echo "发现现有的 gunicorn 进程，PID: $PIDS。正在终止..."
    # 杀掉这些进程
    kill -9 $PIDS
    sleep 2  # 给进程一些时间来终止

    # 再次确认是否有未被杀掉的进程
    PIDS_REMAIN=$(pgrep -f 'runserver:app')
    if [ -n "$PIDS_REMAIN" ]; then
        echo "一些 gunicorn 进程仍在运行: $PIDS_REMAIN。退出中。"
        exit 1
    else
        echo "现有的 gunicorn 进程已成功终止。"
    fi
else
    echo "未发现现有的 gunicorn 进程。"
fi

# 启动 gunicorn 服务器
../venv/bin/gunicorn --worker-class=gthread --log-level debug -w 1 --threads 10 --timeout 120 -b 0.0.0.0:9999 runserver:app -D --access-logfile /root/apps/chatgpt-wecom/logs/access.log --error-logfile /root/apps/chatgpt-wecom/logs/error.log

# 检查是否启动成功，并给予提示
if [ $? -eq 0 ]; then
    echo "服务器启动成功"
else
    echo "服务器启动失败"
fi
