#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
YOLO_MODEL_DIR="${YOLO_MODEL_DIR:-${PROJECT_ROOT}/models}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-${PROJECT_ROOT}/vendor/llama.cpp}"
QWEN_MODEL_DIR="${QWEN_MODEL_DIR:-${PROJECT_ROOT}/models/qwen}"

PROJECT_DIR="${PROJECT_ROOT}"
YOLO_DIR="${YOLO_MODEL_DIR}"

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
  bash -lc "python scripts/single_video_yolo.py \
    --source rtsp://127.0.0.1:8554/cam1 \
    --output /workspace/project/outputs/docker_rtsp_cam1.mp4 \
    --max-frames 100 \
    --imgsz 640"

sudo chown -R lee-server:lee-server "${PROJECT_DIR}"/outputs

echo "Docker RTSP 单路检测完成："
echo "${PROJECT_DIR}/outputs/docker_rtsp_cam1.mp4"
