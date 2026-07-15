# VA 模块开发记录（2026-07-15）

## 一、今日目标

1. 部署并验证 CosmoEdge x86 Docker 容器。
2. 部署 MediaMTX，模拟网络摄像机 RTSP 视频源。
3. 将交通视频接入 CosmoEdge。
4. 配置 YOLOv8 车辆检测任务及事件上报流水线。

## 二、运行环境

- 操作系统：Ubuntu 24.04
- CosmoEdge 容器：`cosmo-x86`
- CosmoEdge 镜像：`cosmo:x86-dev`
- MediaMTX 镜像：`local/mediamtx:1.18.2`
- CosmoEdge 管理页面：`http://100.66.1.5:8080`
- RTSP 地址：`rtsp://127.0.0.1:8554/cam1`
- CosmoEdge 容器访问地址：`rtsp://172.18.0.1:8554/cam1`

## 三、已完成工作

### 1. CosmoEdge 部署

- 完成 x86 Docker 镜像构建。
- 成功启动 `cosmo-x86` 容器。
- 验证管理页面可以访问。
- 完成管理员密码修改。

### 2. MediaMTX 与端口冲突处理

MediaMTX 使用 host 网络时，默认 RTSP UDP 端口 8000 与 CosmoEdge WebRTC UDP 8000 冲突。

处理方法：

```yaml
rtspTransports: [tcp]
rtspAddress: :8554
```

处理后 MediaMTX 成功监听 TCP 8554，CosmoEdge 保留 UDP 8000。

### 3. RTSP 模拟视频源

测试视频：

```text
/home/qi/va-test/videos/traffic(1).mp4
```

推流参数：

- H.264 High Profile
- 1280×720
- 12 FPS
- RTSP over TCP
- 循环播放

验证结果：

- FFmpeg 推流正常。
- FFprobe 可以读取 RTSP 流。
- CosmoEdge 通道状态在线。
- CosmoEdge 可以获取实时通道截图。
- MediaMTX 日志显示 CosmoEdge 正在读取 `cam1`。

### 4. YOLOv8 车辆检测

CosmoEdge 内置模型：

```text
/appfs/cosmo_wander/cwai_data/resource/models/prod_X86_9275710_YOLOV8_V1.0.0/model.onnx
```

已将 COCO 标签配置为：

- ID 2：car
- ID 3：motorcycle
- ID 5：bus
- ID 7：truck

使用 Ultralytics 和 ONNX Runtime GPU 对测试截图进行独立验证，检测结果包括：

- 8 辆汽车
- 1 辆公交车
- 1 名行人
- 单次模型推理约 6.9 ms

因此确认 YOLOv8 ONNX 模型及车辆类别映射正常。

### 5. 车辆检测任务

创建场景任务：`车辆检测`

配置内容：

- 视频通道：`车辆测试流`
- 检测区域：全画面车辆检测区
- 检测类别：car、motorcycle、bus、truck
- 置信度：0.35
- 告警间隔：10 秒
- 告警次数：1
- 运行策略：全天候

当前流水线：

```text
视频解码 → 目标检测算法 → 目标判断 → 事件上报
```

目标判断条件采用车辆类别之间的“或”关系。

## 四、新增脚本与配置

- `configs/mediamtx/mediamtx.yml`
- `scripts/start_mediamtx.sh`
- `scripts/start_rtsp_cam1.sh`

## 五、当前遗留问题

1. YOLOv8 模型可以检测到车辆，但 CosmoEdge 事件中心暂未生成事件。
2. `/data/cwaiuserdata/event` 当前没有事件文件。
3. 后续需要继续检查目标判断和事件上报组件的运行日志。
4. 实时大屏偶尔显示无视频信号，但通道截图、RTSP 取流和模型推理正常。

## 六、下一步计划

1. 定位目标判断与事件上报未触发原因。
2. 验证 HTTP 或 MQTT 结构化事件推送。
3. 部署 MiniCPM-V，并绑定服务器 GPU 0。
4. 设计车辆事件提示词和 RAG 查询问题模板。
5. 通过 HTTP 与 UltraRAG 容器联调。

