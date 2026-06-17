#!/usr/bin/env bash
set -e

PROJECT_DIR="/home/lee-server/vlm-yolo-rtsp-system"
YOLO_DIR="/home/lee-server/yolov8"
HOST_HOME="/home/lee-server"

sudo docker run --rm \
  --network host \
  -e YOLO_CONFIG_DIR=/tmp/Ultralytics \
  -v ${PROJECT_DIR}:/workspace/vlm-yolo-rtsp-system \
  -v ${YOLO_DIR}:/workspace/yolov8 \
  -v ${HOST_HOME}:/host_home \
  vlm-yolo-collab:0.1 \
  bash -lc "yolo predict \
    model=/workspace/yolov8/yolo26n.pt \
    source=/host_home/a.png \
    imgsz=640 \
    conf=0.25 \
    device=cpu \
    project=/workspace/vlm-yolo-rtsp-system/outputs \
    name=docker_yolo_test \
    exist_ok=True"

sudo chown -R lee-server:lee-server ${PROJECT_DIR}/outputs/docker_yolo_test

echo "Docker YOLO 单图检测完成："
echo "${PROJECT_DIR}/outputs/docker_yolo_test"
