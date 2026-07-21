#!/usr/bin/env python3
"""YOLO 事件 -> MiniCPM-V 图像描述与 RAG 查询问题。"""

import argparse
import base64
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import cv2


EVENT_ROOT = Path("/home/qi/va-test/http-events-v2")
MINICPM_URL = "http://127.0.0.1:18091/v1/chat/completions"
MINICPM_MODEL = "/models/MiniCPM-V-4.6"


def utc_now():
    return datetime.now(timezone.utc).astimezone().isoformat()


def atomic_write_json(path: Path, data: dict):
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)


def get_vehicle_count(event: dict):
    prop = event.get("sourceMetadata", {}).get("property", {})
    return prop.get("vehicleCount", "未知")


def get_image_path(event_dir: Path):
    for name in ("annotated.jpg", "detected.jpg", "original.jpg"):
        candidate = event_dir / "images" / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"事件目录没有可用图片：{event_dir}")


def image_to_data_url(image_path: Path):
    image = cv2.imread(str(image_path))
    if image is None:
        raise RuntimeError(f"无法读取图片：{image_path}")

    height, width = image.shape[:2]
    scale = min(1.0, 512 / max(height, width))
    if scale < 1.0:
        image = cv2.resize(image, (round(width * scale), round(height * scale)))

    ok, encoded = cv2.imencode(
        ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80]
    )
    if not ok:
        raise RuntimeError("图片压缩失败")

    image_b64 = base64.b64encode(encoded.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{image_b64}"


def extract_json(text: str):
    """兼容模型偶尔输出 ```json 代码块的情况。"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "sceneDescription": text,
            "trafficSituation": "模型未按 JSON 格式返回",
            "ragQuery": "请结合交通管理知识，分析当前车辆检测事件是否需要关注。",
        }


def call_minicpm(event: dict, image_path: Path):
    vehicle_count = get_vehicle_count(event)
    channel_name = event.get("device", {}).get("channelName", "未知视频通道")

    prompt = f"""
你是视频分析系统中的视觉语义审核模块。
当前视频通道：{channel_name}。
YOLOv8 已检测到车辆数量：{vehicle_count}。

请结合图片和上述 YOLO 信息，严格只输出一个合法 JSON 对象，不要 Markdown，不要解释。
JSON 必须包含以下三个字段：
{{
  "sceneDescription": "用一两句话客观描述画面、道路场景和车辆活动",
  "trafficSituation": "简要说明车流情况，例如稀疏、一般、较密集或拥堵迹象；不确定时明确写不确定",
  "ragQuery": "生成一个可发送给交通管理知识库的中文查询问题，围绕当前车辆数量和道路场景的管理建议"
}}
""".strip()

    payload = {
        "model": MINICPM_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_to_data_url(image_path)},
                },
                {"type": "text", "text": prompt},
            ],
        }],
        "max_tokens": 260,
        "temperature": 0.2,
    }

    request = Request(
        MINICPM_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"MiniCPM HTTP {exc.code}: {detail}") from exc

    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"MiniCPM 未返回有效内容：{result}")

    return extract_json(content), content


def process_event(event_path: Path):
    event_dir = event_path.parent
    output_path = event_dir / "vlm_analysis.json"

    if output_path.exists():
        return False

    event = json.loads(event_path.read_text(encoding="utf-8"))
    image_path = get_image_path(event_dir)

    analysis, raw_response = call_minicpm(event, image_path)

    result = {
        "schemaVersion": "va-vlm-analysis-v1.0",
        "messageId": event.get("messageId"),
        "analyzedAt": utc_now(),
        "vlm": {
            "model": MINICPM_MODEL,
            "endpoint": MINICPM_URL,
            "inputImage": str(image_path.relative_to(event_dir)),
        },
        "yoloSummary": {
            "vehicleCount": get_vehicle_count(event),
            "confidenceThreshold": event.get(
                "sourceMetadata", {}
            ).get("property", {}).get("confidenceThreshold"),
        },
        "analysis": analysis,
        "rawModelResponse": raw_response,
        "ragStatus": "pending",
    }

    atomic_write_json(output_path, result)
    logging.info(
        "处理成功 messageId=%s, RAG问题=%s",
        event.get("messageId"),
        analysis.get("ragQuery"),
    )
    return True


def scan_once(limit: int):
    event_paths = sorted(
        EVENT_ROOT.glob("**/event.json"),
        key=lambda path: path.stat().st_mtime,
    )

    pending = [
        path for path in event_paths
        if not (path.parent / "vlm_analysis.json").exists()
    ]

    if limit > 0:
        pending = pending[:limit]

    if not pending:
        logging.info("没有待处理的新事件")
        return 0

    success_count = 0
    for event_path in pending:
        try:
            if process_event(event_path):
                success_count += 1
        except Exception as exc:
            logging.exception("处理失败：%s，原因：%s", event_path, exc)

    return success_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="只扫描并处理一次，然后退出",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="持续运行时的扫描间隔（秒）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="单次最多处理数量；0 表示不限制",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if not EVENT_ROOT.exists():
        raise RuntimeError(f"事件目录不存在：{EVENT_ROOT}")

    if args.once:
        scan_once(args.limit)
        return

    logging.info("VLM 事件分析器已启动，监听目录：%s", EVENT_ROOT)
    while True:
        scan_once(args.limit)
        time.sleep(max(args.interval, 1))


if __name__ == "__main__":
    main()
