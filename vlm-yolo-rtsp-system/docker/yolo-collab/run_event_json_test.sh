#!/usr/bin/env bash
set -e

PROJECT_DIR="/home/lee-server/vlm-yolo-rtsp-system"
YOLO_DIR="/home/lee-server/yolov8"
LLAMA_DIR="/home/lee-server/llama.cpp"
MODELSCOPE_DIR="/home/lee-server/.cache/modelscope"

sudo docker run --rm \
  --network host \
  -e YOLO_CONFIG_DIR=/tmp/Ultralytics \
  -e OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" \
  -v ${PROJECT_DIR}:${PROJECT_DIR} \
  -v ${YOLO_DIR}:${YOLO_DIR} \
  -v ${LLAMA_DIR}:${LLAMA_DIR} \
  -v ${MODELSCOPE_DIR}:${MODELSCOPE_DIR} \
  -w ${PROJECT_DIR} \
  vlm-yolo-collab:0.1 \
  bash -lc "python scripts/yolo_qwen_event_json_demo.py"

sudo chown -R lee-server:lee-server ${PROJECT_DIR}/outputs

echo "Docker 事件 JSON 协同测试完成"
echo "关键帧目录：${PROJECT_DIR}/outputs/keyframes"
echo "Qwen日志目录：${PROJECT_DIR}/outputs/event_logs"
echo "JSON目录：${PROJECT_DIR}/outputs/event_json"
