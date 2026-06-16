# VLM-YOLO RTSP 多路视频检测系统

本目录用于记录和管理 YOLO26 与 RTSP 多路视频流检测系统的工程脚本，为后续接入 Qwen3-VL 视觉语言模型和 Docker Compose 一键部署做准备。

## 当前已完成

- YOLO26 单图目标检测
- Qwen3-VL 单图语义理解
- YOLO26 + Qwen3-VL 单图协同分析
- 单路本地视频 YOLO 检测
- Docker 部署 MediaMTX RTSP 服务端
- FFmpeg 本地视频推 RTSP 流
- 单路 RTSP 视频流 YOLO 检测
- 三路 RTSP 视频流推流
- 三路 YOLO26 多路检测
- 一键启动、一键检测、一键停止脚本整理

## 项目结构

vlm-yolo-rtsp-system/
  configs/
  logs/
  outputs/
  scripts/
    start_mediamtx.sh
    start_streams.sh
    check_streams.sh
    run_multi_yolo.sh
    stop_all.sh
    multi_rtsp_yolo.py
    single_video_yolo.py

## 使用方法

进入工程目录：

cd ~/vlm-yolo-rtsp-system

启动 MediaMTX RTSP 服务端：

./scripts/start_mediamtx.sh

启动三路 RTSP 推流：

./scripts/start_streams.sh

检查三路视频流：

./scripts/check_streams.sh

运行三路 YOLO26 检测：

./scripts/run_multi_yolo.sh

停止全部服务：

./scripts/stop_all.sh

## 今日测试结果

三路 YOLO26 检测成功完成：

总处理帧数：900
总平均 FPS：37.53
cam1：300 帧，平均 FPS 12.51
cam2：300 帧，平均 FPS 12.51
cam3：300 帧，平均 FPS 12.51

输出视频保存在：

outputs/cam1_detect.mp4
outputs/cam2_detect.mp4
outputs/cam3_detect.mp4

由于视频文件较大，outputs、logs 和 mp4 文件不上传到 Gitee。

## 后续计划

- 将 YOLO 多路检测模块 Docker 化
- 将 FFmpeg 推流模块 Docker 化
- 编写 docker-compose.yml 实现一键启动
- 接入 Qwen3-VL 进行关键帧语义分析
- 增加检测日志、报警记录和多路视频展示界面
