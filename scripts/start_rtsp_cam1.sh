#!/usr/bin/env bash
set -euo pipefail

VIDEO_FILE="${VIDEO_FILE:-/home/qi/va-test/videos/traffic(1).mp4}"
RTSP_URL="${RTSP_URL:-rtsp://127.0.0.1:8554/cam1}"
LOG_FILE="${LOG_FILE:-/home/qi/va-mediamtx/ffmpeg-cam1.log}"

if [[ ! -f "$VIDEO_FILE" ]]; then
    echo "视频文件不存在：$VIDEO_FILE"
    exit 1
fi

if pgrep -af ffmpeg | grep -F -- "$RTSP_URL" >/dev/null; then
    echo "RTSP 推流已经运行：$RTSP_URL"
    exit 0
fi

nohup ffmpeg -re -stream_loop -1 \
    -i "$VIDEO_FILE" \
    -vf "scale=1280:720,fps=12,format=yuv420p" \
    -c:v libx264 \
    -preset veryfast \
    -tune zerolatency \
    -profile:v high \
    -level:v 4.0 \
    -g 24 \
    -keyint_min 24 \
    -sc_threshold 0 \
    -bf 0 \
    -an \
    -f rtsp \
    -rtsp_transport tcp \
    "$RTSP_URL" \
    > "$LOG_FILE" 2>&1 &

echo $! > /home/qi/va-mediamtx/ffmpeg-cam1.pid
echo "RTSP 推流已启动，PID：$!"
echo "地址：$RTSP_URL"
