#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
YOLO_MODEL_DIR="${YOLO_MODEL_DIR:-${PROJECT_ROOT}/models}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-${PROJECT_ROOT}/vendor/llama.cpp}"
QWEN_MODEL_DIR="${QWEN_MODEL_DIR:-${PROJECT_ROOT}/models/qwen}"

PROJECT_DIR="${PROJECT_ROOT}"
YOLO_DIR="${YOLO_MODEL_DIR}"
TEST_IMAGE_PATH="${TEST_IMAGE_PATH:-${PROJECT_ROOT}/assets/a.png}"

sudo docker run --rm \
  --network host \
  -e YOLO_CONFIG_DIR=/tmp/Ultralytics \
  -v "${PROJECT_DIR}:/workspace/project" \
  -v "${YOLO_DIR}:/models:ro" \
  -v "${TEST_IMAGE_PATH}:/input/image:ro" \
  -w /workspace/project \
  vlm-yolo-collab:0.1 \
  bash -lc "yolo predict \
    model=/models/yolo26n.pt \
    source=/input/image \
    imgsz=640 \
    conf=0.25 \
    device=cpu \
    project=/workspace/project/outputs \
    name=docker_yolo_test \
    exist_ok=True"

sudo chown -R lee-server:lee-server "${PROJECT_DIR}"/outputs/docker_yolo_test

echo "Docker YOLO 单图检测完成："
echo "${PROJECT_DIR}/outputs/docker_yolo_test"
