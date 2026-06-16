#!/bin/bash

echo "========== 启动 MediaMTX RTSP 服务 =========="

sudo docker rm -f mediamtx 2>/dev/null

sudo docker run -d \
  --network host \
  --name mediamtx \
  local/mediamtx:1.18.2

echo "MediaMTX 已启动"
sudo docker ps | grep mediamtx
