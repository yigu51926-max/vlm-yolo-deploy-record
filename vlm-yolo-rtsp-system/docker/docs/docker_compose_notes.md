# docker-compose 编排运行说明

## 一、当前编排目标

本项目当前已完成 docker-compose 初版编排，用于统一管理 Docker 化部署流程。

当前 docker-compose.yml 主要包含两个服务：

1. mediamtx：RTSP 流媒体服务。
2. yolo-event：YOLO26 + Qwen3-VL 事件协同容器。

其中，mediamtx 用于提供 RTSP 服务；yolo-event 用于读取三路 RTSP 视频流，运行 YOLO26 检测目标，并在检测到 person 事件后调用 Qwen3-VL 进行关键帧语义分析，最终生成增强版事件 JSON。

当前 FFmpeg 三路推流仍然使用原有脚本启动，暂未放入 docker-compose 中，以保证系统稳定性。

## 二、启动 MediaMTX 服务

当前服务器使用的是旧版 docker-compose 命令，因此运行 compose 时需要使用 sudo。

启动 MediaMTX：

    cd ~/vlm-yolo-rtsp-system
    sudo docker-compose up -d mediamtx

查看服务状态：

    sudo docker-compose ps

如果 mediamtx 状态为 Up，说明 RTSP 服务已启动成功。

## 三、启动三路 RTSP 推流

MediaMTX 启动后，继续使用原有脚本启动三路 RTSP 推流：

    cd ~/vlm-yolo-rtsp-system
    ./scripts/start_streams.sh
    ./scripts/check_streams.sh

正常情况下应看到 cam1、cam2、cam3 均能输出 width、height 和 r_frame_rate 信息。

三路 RTSP 地址分别为：

    rtsp://127.0.0.1:8554/cam1
    rtsp://127.0.0.1:8554/cam2
    rtsp://127.0.0.1:8554/cam3

## 四、运行 YOLO + Qwen 事件协同容器

三路 RTSP 正常后，使用 compose 运行事件协同容器：

    cd ~/vlm-yolo-rtsp-system
    sudo docker-compose --profile event run --rm yolo-event

该命令会执行：

    python scripts/yolo_qwen_event_json_demo.py

运行流程为：

    三路 RTSP 视频流
    → YOLO26 检测 person
    → 保存事件关键帧
    → 调用 Qwen3-VL 分析关键帧
    → 保存 Qwen 原始日志
    → 生成增强版 event_json

## 五、输出目录说明

事件协同运行完成后，主要输出目录如下：

    outputs/keyframes/
    outputs/event_logs/
    outputs/event_json/

其中：

- outputs/keyframes/：保存事件触发关键帧。
- outputs/event_logs/：保存 Qwen3-VL 原始分析日志。
- outputs/event_json/：保存结构化事件 JSON。

每个事件 JSON 中主要包含：

    event_id
    stream_name
    risk_level
    risk_reason
    recommended_action
    qwen_summary
    keyframe_path
    qwen_log_path
    detected_objects

## 六、检查事件 JSON

运行完成后，可使用以下命令检查最新事件 JSON：

    cd ~/vlm-yolo-rtsp-system
    ls -lh outputs/event_json

也可以打开 event_001.json、event_002.json、event_003.json，检查其中是否包含 risk_level、risk_reason、recommended_action 和 qwen_summary 字段。

## 七、停止服务

停止 FFmpeg 推流和相关脚本：

    cd ~/vlm-yolo-rtsp-system
    ./scripts/stop_all.sh

停止 docker-compose 管理的服务：

    sudo docker-compose down

查看是否还有运行中的 Docker 容器：

    sudo docker ps

如果只剩表头，说明容器已全部停止。

## 八、当前状态

截至当前阶段，docker-compose 初版已完成以下能力：

- docker-compose 管理 MediaMTX 服务。
- docker-compose 按需运行 yolo-event 协同容器。
- yolo-event 可读取三路 RTSP。
- YOLO26 可触发 person 事件。
- Qwen3-VL 可完成关键帧语义分析。
- 系统可生成增强版 event_json。

后续可继续扩展：

1. 将 FFmpeg 三路推流也纳入 docker-compose 编排。
2. 增加后台服务容器。
3. 增加前端页面服务。
4. 后续探索 GPU 版 YOLO 容器。
