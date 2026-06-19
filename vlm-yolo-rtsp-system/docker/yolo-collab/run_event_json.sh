#!/usr/bin/env bash
set -e

PROJECT_DIR="/home/lee-server/vlm-yolo-rtsp-system"
YOLO_DIR="/home/lee-server/yolov8"
LLAMA_DIR="/home/lee-server/llama.cpp"
MODELSCOPE_DIR="/home/lee-server/.cache/modelscope"

echo "========== Docker 版 YOLO26 + Qwen3-VL 事件协同运行 =========="
echo "项目目录：${PROJECT_DIR}"
echo "YOLO模型目录：${YOLO_DIR}"
echo "llama.cpp目录：${LLAMA_DIR}"
echo "ModelScope缓存目录：${MODELSCOPE_DIR}"
echo "输出目录：${PROJECT_DIR}/outputs"
echo "============================================================"

mkdir -p ${PROJECT_DIR}/outputs/keyframes
mkdir -p ${PROJECT_DIR}/outputs/event_logs
mkdir -p ${PROJECT_DIR}/outputs/event_json

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

echo "========== Docker 事件协同运行完成 =========="
echo "关键帧目录：${PROJECT_DIR}/outputs/keyframes"
echo "Qwen日志目录：${PROJECT_DIR}/outputs/event_logs"
echo "JSON目录：${PROJECT_DIR}/outputs/event_json"
echo "================================================"
