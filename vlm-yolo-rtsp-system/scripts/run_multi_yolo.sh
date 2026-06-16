#!/bin/bash

echo "========== 启动三路 YOLO26 检测 =========="

cd /home/lee-server/vlm-yolo-rtsp-system

OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" python scripts/multi_rtsp_yolo.py \
  --imgsz 640 \
  --max-frames 300 \
  --output-dir /home/lee-server/vlm-yolo-rtsp-system/outputs
