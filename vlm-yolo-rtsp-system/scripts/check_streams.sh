#!/bin/bash
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

echo "========== 检查三路 RTSP 视频流 =========="

for cam in cam1 cam2 cam3
do
  echo "===== $cam ====="
  ffprobe -v error -rtsp_transport tcp \
    -select_streams v:0 \
    -show_entries stream=width,height,r_frame_rate \
    -of default=noprint_wrappers=1 \
    rtsp://127.0.0.1:8554/$cam
done
