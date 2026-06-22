# YOLO26 + Qwen3-VL 多路视频协同系统 Docker 化部署方案

## 一、当前系统状态

当前项目已经完成 YOLO26 与 Qwen3-VL 的大小模型协同核心闭环。系统已经能够读取三路 RTSP 视频流，通过 YOLO26 进行实时目标检测，在检测到 person 且置信度达到阈值后保存关键帧，并调用 Qwen3-VL 对关键帧进行语义分析。随后系统会生成结构化事件 JSON，并自动写入 risk_level、risk_reason、recommended_action 和 qwen_summary 等字段。

当前核心链路如下：

三路 RTSP 视频流
-> YOLO26 多路检测
-> person 事件触发
-> 保存关键帧
-> Qwen3-VL 语义分析
-> 保存 Qwen 原始日志
-> 生成结构化事件 JSON
-> 自动写入风险等级、风险原因、建议动作和大模型摘要

## 二、Docker 化目标

Docker 化的目标不是一次性把所有模块完全封装，而是分阶段实现可运行、可迁移、可维护的部署结构。

第一阶段目标：

1. 将 YOLO 协同脚本运行环境封装为 Docker 镜像。
2. 容器内能够访问项目的 configs、scripts 和 outputs。
3. 容器内能够运行 Python 脚本并加载 YOLO26 模型。
4. MediaMTX RTSP 服务先继续使用已有 Docker 容器。
5. Qwen3-VL 和 llama.cpp 初期先保留在宿主机，通过路径挂载或宿主机调用方式接入，避免初期镜像过大。

## 三、模块划分

系统后续可拆分为以下模块：

1. RTSP 服务模块：负责接收和分发视频流，目前使用 MediaMTX。
2. 视频推流模块：负责用 FFmpeg 模拟多路摄像头视频流。
3. YOLO 检测模块：负责读取 RTSP 视频流并进行目标检测。
4. Qwen 分析模块：负责对关键帧进行视觉语言分析。
5. 事件管理模块：负责生成 JSON 事件、清洗日志、输出风险摘要。
6. 后台系统模块：后续负责读取事件 JSON 并进行页面展示。

## 四、第一阶段 Docker 方案

第一阶段优先封装 YOLO 检测与协同脚本运行环境，目录结构如下：

docker/yolo-collab/
├── Dockerfile
└── requirements.txt

容器挂载宿主机项目目录：

${PROJECT_ROOT}:/workspace/project

容器挂载 YOLO 模型目录：

${YOLO_MODEL_DIR}:/models:ro

容器运行目录：

/workspace/project

## 五、第一阶段验证指标

第一阶段 Docker 化完成后，需要验证：

1. 容器能够启动。
2. 容器内 Python 能正常运行。
3. 容器内能导入 cv2、ultralytics、torch。
4. 容器内能访问 configs/collaboration_config.json。
5. 容器内能访问 YOLO26 模型文件。
6. 容器内能运行 YOLO 单图或视频检测脚本。

## 六、后续扩展计划

第一阶段完成后，再逐步推进：

1. 将多路 RTSP YOLO 检测脚本迁移进容器。
2. 将事件 JSON 生成脚本迁移进容器。
3. 设计 Qwen3-VL 的容器调用方式。
4. 编写 docker-compose.yml，统一管理 MediaMTX、YOLO 协同模块和后续后台模块。
5. 建立后台系统，读取 outputs/event_json 并进行可视化展示。
