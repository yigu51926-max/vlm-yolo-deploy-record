#!/bin/bash
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

echo "========== 启动三路 YOLO26 检测 =========="

cd "${PROJECT_ROOT}"

OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" python scripts/multi_rtsp_yolo.py \
  --imgsz 640 \
  --max-frames 300 \
  --output-dir "${PROJECT_ROOT}/outputs"
