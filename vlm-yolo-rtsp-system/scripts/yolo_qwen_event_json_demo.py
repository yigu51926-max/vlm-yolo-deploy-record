import cv2
import json
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO
try:
    from .enhance_event_json import enhance_one_event
    from .event_utils import atomic_write_json, generate_event_id
    from .project_paths import PROJECT_ROOT, resolve_config_paths, resolve_project_path
except ImportError:
    from enhance_event_json import enhance_one_event
    from event_utils import atomic_write_json, generate_event_id
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


def extract_objects(result, model):
    objects = []

    if result.boxes is None or len(result.boxes) == 0:
        return objects

    for box in result.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        name = model.names[cls_id]
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

        objects.append({
            "class_name": name,
            "confidence": round(conf, 4),
            "bbox": [x1, y1, x2, y2]
        })

    return objects


def format_detect_info(objects):
    if not objects:
        return "YOLO检测结果：未检测到明显目标。"

    lines = []
    for obj in objects:
        lines.append(
            f"{obj['class_name']} {obj['confidence']:.2f}, "
            f"bbox={tuple(obj['bbox'])}"
        )

    return "YOLO检测结果：\n" + "\n".join(lines)


def should_trigger(objects, target_class, conf_threshold):
    for obj in objects:
        if obj["class_name"] == target_class and obj["confidence"] >= conf_threshold:
            return True
    return False


def infer_risk_level(objects):
    class_names = {obj["class_name"] for obj in objects}

    has_person = "person" in class_names
    has_vehicle = any(v in class_names for v in ["car", "truck", "bus", "motorcycle"])
    has_equipment = any(e in class_names for e in ["laptop", "chair", "bottle"])

    if has_person and has_vehicle:
        return "warning"

    if has_person and has_equipment:
        return "normal"

    if has_person:
        return "normal"

    return "normal"


def save_keyframe(frame, result, keyframe_dir, stream_name, event_id):
    keyframe_dir = Path(keyframe_dir)
    keyframe_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{event_id}_{stream_name}.jpg"
    path = keyframe_dir / filename

    plotted = result.plot()
    cv2.imwrite(str(path), plotted)

    return str(path)


def call_qwen(config_path, image_path, detect_info, event_id, event_log_dir):
    log_path = Path(event_log_dir) / f"qwen_analysis_{event_id}.txt"

    cmd = [
        "python",
        "scripts/qwen_analyze_image.py",
        "--config", config_path,
        "--image", image_path,
        "--detect-info", detect_info,
        "--event-id", event_id
    ]

    print("=" * 80)
    print("[触发 Qwen3-VL 分析]")
    print(f"[关键帧] {image_path}")
    print("=" * 80)

    process = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT
    )

    return process.returncode, str(log_path)


def save_event_json(event_json_dir, event_data):
    event_json_dir = Path(event_json_dir)
    event_json_dir.mkdir(parents=True, exist_ok=True)

    event_id = event_data["event_id"]
    path = event_json_dir / f"{event_id}.json"

    return str(atomic_write_json(path, event_data))


def main():
    parser = argparse.ArgumentParser(description="YOLO26 + Qwen3-VL JSON事件日志协同原型")
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
    event_log_dir = outputs_cfg["event_log_dir"]
    event_json_dir = outputs_cfg["event_json_dir"]

    print("=" * 80)
    print("[启动] YOLO26 + Qwen3-VL JSON事件日志协同原型")
    print(f"[YOLO模型] {model_path}")
    print(f"[触发类别] {target_class}")
    print(f"[触发置信度] {person_conf}")
    print(f"[最大事件数] {max_events}")
    print(f"[JSON目录] {event_json_dir}")
    print("=" * 80)

    model = YOLO(model_path)

    caps = []
    names = []
    urls = []
    frame_counts = []
    last_trigger_time = {}

    for stream in streams:
        name = stream["name"]
        url = stream["url"]

        cap, width, height, fps = open_capture(url)

        caps.append(cap)
        names.append(name)
        urls.append(url)
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

            for local_i, result in enumerate(results):
                idx = active_indices[local_i]
                frame = frames[local_i]
                stream_name = names[idx]
                stream_url = urls[idx]
                now = time.time()

                objects = extract_objects(result, model)

                if not should_trigger(objects, target_class, person_conf):
                    continue

                if now - last_trigger_time[stream_name] < cooldown_seconds:
                    continue

                total_events += 1
                event_id = generate_event_id()
                last_trigger_time[stream_name] = now

                detect_info = format_detect_info(objects)
                risk_level = infer_risk_level(objects)

                keyframe_path = save_keyframe(
                    frame=frame,
                    result=result,
                    keyframe_dir=keyframe_dir,
                    stream_name=stream_name,
                    event_id=event_id
                )

                print("=" * 80)
                print(f"[事件触发] {event_id}")
                print(f"[视频流] {stream_name}")
                print(f"[原因] 检测到 {target_class} 且置信度 >= {person_conf}")
                print(f"[风险等级] {risk_level}")
                print(f"[关键帧] {keyframe_path}")
                print(detect_info)
                print("=" * 80)

                qwen_returncode, qwen_log_path = call_qwen(
                    config_path=args.config,
                    image_path=keyframe_path,
                    detect_info=detect_info,
                    event_id=event_id,
                    event_log_dir=event_log_dir
                )

                event_data = {
                    "event_id": event_id,
                    "stream_name": stream_name,
                    "stream_url": stream_url,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "trigger_reason": f"检测到 {target_class} 且置信度达到阈值 {person_conf}",
                    "risk_level": risk_level,
                    "keyframe_path": keyframe_path,
                    "qwen_log_path": qwen_log_path,
                    "qwen_returncode": qwen_returncode,
                    "detected_objects": objects
                }

                event_json_path = save_event_json(event_json_dir, event_data)

                try:
                    enhance_one_event(event_json_path)
                    print(f"[JSON事件日志] {event_json_path}")
                    print("[JSON增强] 已写入 qwen_summary / risk_reason / recommended_action")
                except Exception as e:
                    print(f"[JSON增强警告] {e}")
                    print(f"[JSON事件日志] {event_json_path}")

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
    print("[完成] YOLO26 + Qwen3-VL JSON事件日志协同原型结束")
    print(f"[总处理帧数] {total_frames}")
    print(f"[平均FPS] {avg_fps:.2f}")
    print(f"[触发事件数] {total_events}")
    print(f"[关键帧目录] {keyframe_dir}")
    print(f"[Qwen日志目录] {event_log_dir}")
    print(f"[JSON日志目录] {event_json_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
