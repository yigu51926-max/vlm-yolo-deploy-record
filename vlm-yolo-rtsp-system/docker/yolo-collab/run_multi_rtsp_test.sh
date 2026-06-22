#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
YOLO_MODEL_DIR="${YOLO_MODEL_DIR:-${PROJECT_ROOT}/models}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-${PROJECT_ROOT}/vendor/llama.cpp}"
QWEN_MODEL_DIR="${QWEN_MODEL_DIR:-${PROJECT_ROOT}/models/qwen}"

PROJECT_DIR="${PROJECT_ROOT}"
YOLO_DIR="${YOLO_MODEL_DIR}"
MULTI_OUTPUT_DIR="${PROJECT_ROOT}/outputs/docker_multi_rtsp"

mkdir -p "${MULTI_OUTPUT_DIR}"

sudo docker run --rm \
  --network host \
  -e YOLO_CONFIG_DIR=/tmp/Ultralytics \
  -e OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" \
  -e YOLO_MODEL_PATH=/models/yolo26n.pt \
  -e LLAMA_CLI_PATH=/opt/llama.cpp/build/bin/llama-cli \
  -e QWEN_MODEL_PATH=/models/qwen/Qwen3VL-2B-Instruct-Q4_K_M.gguf \
  -e QWEN_MMPROJ_PATH=/models/qwen/mmproj-Qwen3VL-2B-Instruct-F16.gguf \
  -v "${PROJECT_DIR}:/workspace/project" \
  -v "${YOLO_DIR}:/models:ro" \
  -w /workspace/project \
  vlm-yolo-collab:0.1 \
  bash -lc "python scripts/multi_rtsp_yolo.py \
    --imgsz 640 \
    --max-frames 100"

sudo chown -R lee-server:lee-server "${MULTI_OUTPUT_DIR}"

echo "Docker 三路 RTSP 检测完成"
echo "输出目录：${MULTI_OUTPUT_DIR}"
