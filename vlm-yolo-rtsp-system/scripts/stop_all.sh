#!/bin/bash
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

echo "========== 停止 FFmpeg 三路推流 =========="
pkill -f "rtsp://127.0.0.1:8554/cam" 2>/dev/null

sleep 1

echo "========== 停止 MediaMTX 容器 =========="
sudo docker stop mediamtx 2>/dev/null

echo "========== 当前 FFmpeg 进程 =========="
ps aux | grep ffmpeg | grep -v grep || echo "没有 FFmpeg 推流进程"

echo "========== 当前 Docker 容器 =========="
sudo docker ps

echo "全部服务已停止"
