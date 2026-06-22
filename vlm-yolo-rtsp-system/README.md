# VLM-YOLO RTSP 多路视频检测系统

本目录是项目唯一运行根目录。脚本、配置、输出和 Docker Compose 都以当前目录为基准，不依赖固定的用户主目录。

## 目录

```text
vlm-yolo-rtsp-system/
├── backend/                 # FastAPI 事件看板
├── configs/                 # YOLO + Qwen 协同配置
├── docker/                  # 镜像和 Docker 测试脚本
├── models/                  # 默认模型目录（模型文件不提交）
├── outputs/                 # 当前仓库内的运行输出
├── scripts/                 # 推流、检测和协同脚本
└── docker-compose.yml
```

## 路径配置

默认路径相对本目录解析：

- YOLO：`models/yolo26n.pt`
- llama.cpp：`vendor/llama.cpp/build/bin/llama-cli`
- Qwen：`models/qwen/`
- 测试视频：`assets/test.mp4`
- 测试图片：`assets/a.png`
- 输出：`outputs/`

模型和测试素材不随仓库提交。启动检测或推流前，必须将文件放入上述默认位置，或者通过环境变量指向现有文件：

```bash
export YOLO_MODEL_PATH=/path/to/yolo26n.pt
export LLAMA_CLI_PATH=/path/to/llama-cli
export QWEN_MODEL_PATH=/path/to/Qwen3VL-2B-Instruct-Q4_K_M.gguf
export QWEN_MMPROJ_PATH=/path/to/mmproj-Qwen3VL-2B-Instruct-F16.gguf
export TEST_VIDEO_PATH=/path/to/test.mp4
export TEST_IMAGE_PATH=/path/to/a.png
```

## 宿主机启动

Shell 脚本会自行定位项目根目录。以下命令从 Git 仓库根目录进入主工程：

```bash
cd vlm-yolo-rtsp-system
```

后台看板只读取已有 `outputs` 数据，不要求模型文件；YOLO、Qwen 和推流命令则要求先完成上面的模型或素材路径配置。

启动 MediaMTX：

```bash
./scripts/start_mediamtx.sh
```

启动并检查三路测试 RTSP：

```bash
./scripts/start_streams.sh
./scripts/check_streams.sh
```

运行三路 YOLO：

```bash
./scripts/run_multi_yolo.sh
```

运行 YOLO + Qwen 事件协同：

```bash
python scripts/yolo_qwen_event_json_demo.py
```

启动后台看板：

```bash
python -m uvicorn backend.dashboard_server:app --host 0.0.0.0 --port 8000
```

访问 `http://服务器地址:8000/`。

停止推流和 MediaMTX：

```bash
./scripts/stop_all.sh
```

## Docker Compose

Compose 始终挂载当前目录。模型目录可通过环境变量指定：

```bash
export YOLO_MODEL_DIR=/path/to/yolo-model-directory
export LLAMA_CPP_DIR=/path/to/llama.cpp
export QWEN_MODEL_DIR=/path/to/qwen-model-directory

docker-compose config
sudo docker-compose up -d mediamtx
sudo docker-compose --profile event run --rm yolo-event
```

未设置变量时，Compose 默认使用本目录下的 `models/`、`vendor/llama.cpp/` 和 `models/qwen/`。

## 输出

运行数据保存在当前项目的 `outputs/`：

- `outputs/keyframes/`
- `outputs/event_logs/`
- `outputs/event_json/`
- `outputs/docker_multi_rtsp/`

`outputs/` 是普通目录，不再链接到仓库外部路径；运行数据仍由 `.gitignore` 忽略。
