import os
import cv2
import time
import argparse
from urllib.parse import urlparse
from ultralytics import YOLO


def stream_name(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return path.replace("/", "_") if path else "stream"


def open_capture(source: str):
    cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频流：{source}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    fps = cap.get(cv2.CAP_PROP_FPS)

    if not fps or fps <= 1:
        fps = 12.0

    return cap, width, height, fps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources",
        nargs="+",
        default=[
            "rtsp://127.0.0.1:8554/cam1",
            "rtsp://127.0.0.1:8554/cam2",
            "rtsp://127.0.0.1:8554/cam3",
        ],
        help="多路RTSP地址"
    )
    parser.add_argument("--model", default="/home/lee-server/yolov8/yolo26n.pt")
    parser.add_argument("--output-dir", default="/home/lee-server/vlm-yolo-rtsp-system/outputs/docker_multi_rtsp")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--max-frames", type=int, default=300)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 80)
    print("[启动] 多路 RTSP YOLO26 检测")
    print(f"[模型] {args.model}")
    print(f"[推理尺寸] imgsz={args.imgsz}")
    print(f"[路数] {len(args.sources)}")
    print("=" * 80)

    model = YOLO(args.model)

    caps = []
    writers = []
    names = []
    counts = []

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    for source in args.sources:
        name = stream_name(source)
        cap, width, height, fps = open_capture(source)

        output_path = os.path.join(args.output_dir, f"{name}_detect.mp4")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not writer.isOpened():
            raise RuntimeError(f"无法创建输出视频：{output_path}")

        caps.append(cap)
        writers.append(writer)
        names.append(name)
        counts.append(0)

        print(f"[打开] {name}: {source}")
        print(f"       分辨率={width}x{height}, FPS={fps}, 输出={output_path}")

    start_time = time.time()

    try:
        while True:
            frames = []
            active_indices = []

            for i, cap in enumerate(caps):
                if counts[i] >= args.max_frames:
                    continue

                ret, frame = cap.read()
                if not ret:
                    print(f"[警告] {names[i]} 读取失败，跳过这一帧")
                    continue

                frames.append(frame)
                active_indices.append(i)

            if not frames:
                break

            results = model.predict(
                frames,
                conf=args.conf,
                imgsz=args.imgsz,
                verbose=False
            )

            for result, idx in zip(results, active_indices):
                plotted = result.plot()
                writers[idx].write(plotted)
                counts[idx] += 1

            total = sum(counts)
            if total % 30 == 0:
                elapsed = time.time() - start_time
                total_fps = total / elapsed if elapsed > 0 else 0
                status = ", ".join([f"{names[i]}={counts[i]}" for i in range(len(names))])
                print(f"[进度] 总帧={total}, 总FPS={total_fps:.2f}, {status}")

            if all(c >= args.max_frames for c in counts):
                break

    finally:
        for cap in caps:
            cap.release()
        for writer in writers:
            writer.release()

    elapsed = time.time() - start_time
    total = sum(counts)
    total_fps = total / elapsed if elapsed > 0 else 0

    print("=" * 80)
    print("[完成] 多路 RTSP YOLO26 检测结束")
    print(f"[总处理帧数] {total}")
    print(f"[总平均FPS] {total_fps:.2f}")
    for i, name in enumerate(names):
        print(f"[{name}] 帧数={counts[i]}, 平均FPS={counts[i] / elapsed:.2f}")
    print(f"[输出目录] {args.output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
