#!/usr/bin/env bash
set -e

PROJECT_DIR="/home/lee-server/vlm-yolo-rtsp-system"
YOLO_DIR="/home/lee-server/yolov8"
MULTI_OUTPUT_DIR="/home/lee-server/vlm-yolo-rtsp-system/outputs/docker_multi_rtsp"

mkdir -p ${MULTI_OUTPUT_DIR}

sudo docker run --rm \
  --network host \
  -e YOLO_CONFIG_DIR=/tmp/Ultralytics \
  -e OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" \
  -v ${PROJECT_DIR}:${PROJECT_DIR} \
  -v ${YOLO_DIR}:${YOLO_DIR} \
  -v ${MULTI_OUTPUT_DIR}:${MULTI_OUTPUT_DIR} \
  -w ${PROJECT_DIR} \
  vlm-yolo-collab:0.1 \
  bash -lc "python scripts/multi_rtsp_yolo.py \
    --imgsz 640 \
    --max-frames 100"

sudo chown -R lee-server:lee-server ${MULTI_OUTPUT_DIR}

echo "Docker 三路 RTSP 检测完成"
echo "输出目录：${MULTI_OUTPUT_DIR}"
