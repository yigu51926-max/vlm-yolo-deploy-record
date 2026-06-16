#!/bin/bash

echo "========== 启动三路 RTSP 推流 =========="

pkill -f "rtsp://127.0.0.1:8554/cam" 2>/dev/null

nohup ffmpeg -re -stream_loop -1 \
  -i /home/lee-server/test.mp4 \
  -vf "scale=1280:-2,fps=12" \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -g 12 -bf 0 -pix_fmt yuv420p \
  -an \
  -f rtsp \
  -rtsp_transport tcp \
  rtsp://127.0.0.1:8554/cam1 \
  > /home/lee-server/vlm-yolo-rtsp-system/logs/cam1_push.log 2>&1 &

nohup ffmpeg -re -stream_loop -1 \
  -ss 00:01:00 \
  -i /home/lee-server/test.mp4 \
  -vf "scale=1280:-2,fps=12" \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -g 12 -bf 0 -pix_fmt yuv420p \
  -an \
  -f rtsp \
  -rtsp_transport tcp \
  rtsp://127.0.0.1:8554/cam2 \
  > /home/lee-server/vlm-yolo-rtsp-system/logs/cam2_push.log 2>&1 &

nohup ffmpeg -re -stream_loop -1 \
  -ss 00:02:00 \
  -i /home/lee-server/test.mp4 \
  -vf "scale=1280:-2,fps=12" \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -g 12 -bf 0 -pix_fmt yuv420p \
  -an \
  -f rtsp \
  -rtsp_transport tcp \
  rtsp://127.0.0.1:8554/cam3 \
  > /home/lee-server/vlm-yolo-rtsp-system/logs/cam3_push.log 2>&1 &

sleep 3

echo "当前 FFmpeg 推流进程："
ps aux | grep ffmpeg | grep -v grep
