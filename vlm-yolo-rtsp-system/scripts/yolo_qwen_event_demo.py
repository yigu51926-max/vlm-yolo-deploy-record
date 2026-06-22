import cv2
import json
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO

try:
    from .project_paths import PROJECT_ROOT, resolve_config_paths, resolve_project_path
except ImportError:
    from project_paths import PROJECT_ROOT, resolve_config_paths, resolve_project_path


def load_config(config_path):
    path = resolve_project_path(config_path)
    with path.open("r", encoding="utf-8") as f:
        return resolve_config_paths(json.load(f))


def open_capture(source):
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


def format_detect_info(result, model):
    lines = []

    if result.boxes is None or len(result.boxes) == 0:
        return "YOLO检测结果：未检测到明显目标。"

    for box in result.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        name = model.names[cls_id]
        xyxy = box.xyxy[0].tolist()
        x1, y1, x2, y2 = [int(v) for v in xyxy]

        lines.append(
            f"{name} {conf:.2f}, bbox=({x1},{y1},{x2},{y2})"
        )

    return "YOLO检测结果：\n" + "\n".join(lines)


def should_trigger(result, model, target_class, conf_threshold):
    if result.boxes is None or len(result.boxes) == 0:
        return False

    for box in result.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        name = model.names[cls_id]

        if name == target_class and conf >= conf_threshold:
            return True

    return False


def save_keyframe(frame, result, keyframe_dir, stream_name, event_id):
    keyframe_dir = Path(keyframe_dir)
    keyframe_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{event_id}_{stream_name}_{timestamp}.jpg"
    path = keyframe_dir / filename

    plotted = result.plot()
    cv2.imwrite(str(path), plotted)

    return str(path)


def call_qwen(config_path, image_path, detect_info):
    cmd = [
        "python",
        "scripts/qwen_analyze_image.py",
        "--config", config_path,
        "--image", image_path,
        "--detect-info", detect_info
    ]

    print("=" * 80)
    print("[触发Qwen3-VL分析]")
    print(f"[关键帧] {image_path}")
    print("=" * 80)

    process = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT
    )

    return process.returncode


def main():
    parser = argparse.ArgumentParser(description="YOLO26 触发 Qwen3-VL 关键帧分析原型")
    parser.add_argument("--config", default="configs/collaboration_config.json")
    parser.add_argument("--max-frames", type=int, default=500)
    args = parser.parse_args()

    config = load_config(args.config)

    streams = config["streams"]
    yolo_cfg = config["yolo"]
    trigger_cfg = config["trigger"]
    outputs_cfg = config["outputs"]

    model_path = yolo_cfg["model_path"]
    imgsz = yolo_cfg["imgsz"]
    yolo_conf = yolo_cfg["conf"]

    target_class = trigger_cfg["target_class"]
    person_conf = trigger_cfg["person_conf"]
    cooldown_seconds = trigger_cfg["cooldown_seconds"]
    max_events = trigger_cfg["max_events_per_run"]

    keyframe_dir = outputs_cfg["keyframe_dir"]

    print("=" * 80)
    print("[启动] YOLO26 + Qwen3-VL 大小模型协同原型")
    print(f"[YOLO模型] {model_path}")
    print(f"[触发类别] {target_class}")
    print(f"[触发置信度] {person_conf}")
    print(f"[冷却时间] {cooldown_seconds}s")
    print(f"[最大事件数] {max_events}")
    print("=" * 80)

    model = YOLO(model_path)

    caps = []
    names = []
    frame_counts = []
    last_trigger_time = {}

    for stream in streams:
        name = stream["name"]
        url = stream["url"]

        cap, width, height, fps = open_capture(url)

        caps.append(cap)
        names.append(name)
        frame_counts.append(0)
        last_trigger_time[name] = 0

        print(f"[打开视频流] {name}: {url}")
        print(f"             分辨率={width}x{height}, FPS={fps}")

    total_events = 0
    start_time = time.time()

    try:
        while True:
            frames = []
            active_indices = []

            for i, cap in enumerate(caps):
                if frame_counts[i] >= args.max_frames:
                    continue

                ret, frame = cap.read()

                if not ret:
                    print(f"[警告] {names[i]} 读取失败，跳过")
                    continue

                frames.append(frame)
                active_indices.append(i)
                frame_counts[i] += 1

            if not frames:
                break

            results = model.predict(
                frames,
                imgsz=imgsz,
                conf=yolo_conf,
                verbose=False
            )

            for result, idx in zip(results, active_indices):
                stream_name = names[idx]
                now = time.time()

                if should_trigger(result, model, target_class, person_conf):
                    if now - last_trigger_time[stream_name] < cooldown_seconds:
                        continue

                    total_events += 1
                    event_id = f"event_{total_events:03d}"
                    last_trigger_time[stream_name] = now

                    detect_info = format_detect_info(result, model)
                    keyframe_path = save_keyframe(
                        frame=frames[active_indices.index(idx)],
                        result=result,
                        keyframe_dir=keyframe_dir,
                        stream_name=stream_name,
                        event_id=event_id
                    )

                    print("=" * 80)
                    print(f"[事件触发] {event_id}")
                    print(f"[视频流] {stream_name}")
                    print(f"[原因] 检测到 {target_class} 且置信度 >= {person_conf}")
                    print(f"[关键帧] {keyframe_path}")
                    print(detect_info)
                    print("=" * 80)

                    call_qwen(args.config, keyframe_path, detect_info)

                    if total_events >= max_events:
                        print("[停止] 已达到最大事件数")
                        raise StopIteration

            total_frames = sum(frame_counts)
            if total_frames % 60 == 0:
                elapsed = time.time() - start_time
                fps = total_frames / elapsed if elapsed > 0 else 0
                status = ", ".join([f"{names[i]}={frame_counts[i]}" for i in range(len(names))])
                print(f"[进度] 总帧={total_frames}, FPS={fps:.2f}, 事件数={total_events}, {status}")

            if all(c >= args.max_frames for c in frame_counts):
                break

    except StopIteration:
        pass

    finally:
        for cap in caps:
            cap.release()

    elapsed = time.time() - start_time
    total_frames = sum(frame_counts)
    avg_fps = total_frames / elapsed if elapsed > 0 else 0

    print("=" * 80)
    print("[完成] YOLO26 + Qwen3-VL 协同原型结束")
    print(f"[总处理帧数] {total_frames}")
    print(f"[平均FPS] {avg_fps:.2f}")
    print(f"[触发事件数] {total_events}")
    print(f"[关键帧目录] {keyframe_dir}")
    print(f"[日志目录] {config['outputs']['event_log_dir']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
