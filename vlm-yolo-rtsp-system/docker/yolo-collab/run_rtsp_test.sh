#!/usr/bin/env bash
set -e

PROJECT_DIR="/home/lee-server/vlm-yolo-rtsp-system"
YOLO_DIR="/home/lee-server/yolov8"

sudo docker run --rm \
  --network host \
  -e YOLO_CONFIG_DIR=/tmp/Ultralytics \
  -e OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" \
  -v ${PROJECT_DIR}:${PROJECT_DIR} \
  -v ${YOLO_DIR}:${YOLO_DIR} \
  -w ${PROJECT_DIR} \
  vlm-yolo-collab:0.1 \
  bash -lc "python scripts/single_video_yolo.py \
    --source rtsp://127.0.0.1:8554/cam1 \
    --output ${PROJECT_DIR}/outputs/docker_rtsp_cam1.mp4 \
    --max-frames 100 \
    --imgsz 640"

sudo chown -R lee-server:lee-server ${PROJECT_DIR}/outputs

echo "Docker RTSP 单路检测完成："
echo "${PROJECT_DIR}/outputs/docker_rtsp_cam1.mp4"
