#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
YOLO_MODEL_DIR="${YOLO_MODEL_DIR:-${PROJECT_ROOT}/models}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-${PROJECT_ROOT}/vendor/llama.cpp}"
QWEN_MODEL_DIR="${QWEN_MODEL_DIR:-${PROJECT_ROOT}/models/qwen}"

PROJECT_DIR="${PROJECT_ROOT}"
YOLO_DIR="${YOLO_MODEL_DIR}"
LLAMA_DIR="${LLAMA_CPP_DIR}"
MODELSCOPE_DIR="${QWEN_MODEL_DIR}"

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
  -v "${LLAMA_DIR}:/opt/llama.cpp:ro" \
  -v "${MODELSCOPE_DIR}:/models/qwen:ro" \
  -w /workspace/project \
  vlm-yolo-collab:0.1 \
  bash -lc "python scripts/yolo_qwen_event_json_demo.py"

sudo chown -R lee-server:lee-server "${PROJECT_DIR}"/outputs

echo "Docker 事件 JSON 协同测试完成"
echo "关键帧目录：${PROJECT_DIR}/outputs/keyframes"
echo "Qwen日志目录：${PROJECT_DIR}/outputs/event_logs"
echo "JSON目录：${PROJECT_DIR}/outputs/event_json"
