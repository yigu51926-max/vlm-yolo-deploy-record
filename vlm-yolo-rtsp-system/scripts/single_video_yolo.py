import os
from pathlib import Path
import cv2
import time
import argparse
from ultralytics import YOLO

try:
    from .project_paths import PROJECT_ROOT, resolve_project_path
except ImportError:
    from project_paths import PROJECT_ROOT, resolve_project_path


def run_video(source, model_path, output_path, conf=0.25, imgsz=960, max_frames=300):
    source_path = Path(source).expanduser()
    source = source if source.startswith(("rtsp://", "rtmp://", "http://", "https://")) else str(resolve_project_path(source_path))
    output_path = resolve_project_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    is_stream = source.startswith(("rtsp://", "rtmp://", "http://", "https://"))

    if not is_stream and not Path(source).exists():
        raise FileNotFoundError(f"找不到视频：{source}")

    model_path = resolve_project_path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"找不到YOLO模型：{model_path}")

    model = YOLO(str(model_path))

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频：{source}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS)

    if src_fps <= 1 or src_fps != src_fps:
        src_fps = 25

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, src_fps, (width, height))

    frame_id = 0
    start_time = time.time()

    print("=" * 80)
    print("[启动] 单路视频 YOLO26 检测")
    print(f"[输入视频] {source}")
    print(f"[输出视频] {output_path}")
    print(f"[分辨率] {width}x{height}")
    print(f"[源FPS] {src_fps}")
    print(f"[模型] {model_path}")
    print("=" * 80)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_id += 1

        results = model.predict(
            source=frame,
            conf=conf,
            imgsz=imgsz,
            verbose=False
        )

        result = results[0]
        annotated = result.plot()
        writer.write(annotated)

        if frame_id % 10 == 0:
            elapsed = time.time() - start_time
            real_fps = frame_id / elapsed if elapsed > 0 else 0
            obj_count = len(result.boxes) if result.boxes is not None else 0
            print(f"[Frame {frame_id}] 处理FPS={real_fps:.2f}, 检测目标数={obj_count}")

        if max_frames > 0 and frame_id >= max_frames:
            print(f"[停止] 已达到 max_frames={max_frames}")
            break

    cap.release()
    writer.release()

    elapsed = time.time() - start_time
    avg_fps = frame_id / elapsed if elapsed > 0 else 0

    print("=" * 80)
    print("[完成] 单路视频 YOLO26 检测结束")
    print(f"[总处理帧数] {frame_id}")
    print(f"[平均处理FPS] {avg_fps:.2f}")
    print(f"[结果视频] {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, default=os.environ.get("TEST_VIDEO_PATH", str(PROJECT_ROOT / "assets" / "test.mp4")))
    parser.add_argument("--model", type=str, default=os.environ.get("YOLO_MODEL_PATH", str(PROJECT_ROOT / "models" / "yolo26n.pt")))
    parser.add_argument("--output", type=str, default=str(PROJECT_ROOT / "outputs" / "yolo_video_output.mp4"))
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--max-frames", type=int, default=300)
    args = parser.parse_args()

    run_video(
        source=args.source,
        model_path=args.model,
        output_path=args.output,
        conf=args.conf,
        imgsz=args.imgsz,
        max_frames=args.max_frames
    )


if __name__ == "__main__":
    main()
