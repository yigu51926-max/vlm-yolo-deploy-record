#!/bin/bash
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

echo "========== 启动 MediaMTX RTSP 服务 =========="

sudo docker rm -f mediamtx 2>/dev/null

sudo docker run -d \
  --network host \
  --name mediamtx \
  local/mediamtx:1.18.2

echo "MediaMTX 已启动"
sudo docker ps | grep mediamtx
