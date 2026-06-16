# VLM + YOLO 多模态部署调试记录

本仓库用于记录从 2026-06-15 开始，在远程 Ubuntu 服务器上进行的视觉语言多模态大模型部署、YOLO 检测和多路视频流调试过程。

## 项目内容

本项目围绕 Qwen-VL 本地推理、YOLO 目标检测、单图识别、单路视频检测和多路 RTSP 视频流检测展开。

## 当前脚本

- `yolo_qwen_image_demo.py`：单图 YOLO + Qwen-VL 图像理解测试脚本
- `single_video_yolo.py`：单路视频 YOLO 检测脚本
- `multi_rtsp_yolo.py`：多路 RTSP 视频流 YOLO 检测脚本

## 目录说明

- `scripts/`：关键测试脚本
- `logs/`：终端操作记录和调试日志
- `results/`：运行结果记录
- `notes/`：阶段总结和后续计划

