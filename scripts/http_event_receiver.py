#!/usr/bin/env python3

import base64
import binascii
import io
import json
import os
import re
import shutil
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


HOST = os.environ.get("VA_HTTP_HOST", "0.0.0.0")
PORT = int(os.environ.get("VA_HTTP_PORT", "18090"))

EVENT_DIR = Path(
    os.environ.get(
        "VA_EVENT_DIR",
        "/home/qi/va-test/http-events-v2",
    )
).resolve()

JPEG_QUALITY = int(os.environ.get("VA_JPEG_QUALITY", "70"))
MAX_IMAGE_WIDTH = int(os.environ.get("VA_MAX_IMAGE_WIDTH", "1280"))
MAX_IMAGE_HEIGHT = int(os.environ.get("VA_MAX_IMAGE_HEIGHT", "720"))

MAX_REQUEST_BYTES = int(
    os.environ.get(
        "VA_MAX_REQUEST_BYTES",
        str(20 * 1024 * 1024),
    )
)

EVENT_DIR.mkdir(parents=True, exist_ok=True)

JSONL_LOCK = threading.Lock()

IMAGE_FIELDS = {
    # CosmoEdge 官方字段拼写就是 orignalPicture
    "orignalPicture": "original.jpg",
    "fullPicture": "annotated.jpg",
    "detectedPicture": "detected.jpg",
}


def safe_filename(value: Any) -> str:
    text = str(value or "")
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", text)
    return safe or f"event-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"


def parse_event_time(timestamp: Any) -> datetime:
    try:
        value = float(str(timestamp))

        # CosmoEdge 当前使用毫秒时间戳。
        if value > 10_000_000_000:
            value /= 1000.0

        return datetime.fromtimestamp(value, tz=timezone.utc).astimezone()
    except (TypeError, ValueError, OSError, OverflowError):
        return datetime.now().astimezone()


def decode_base64_image(value: Any) -> bytes:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("图片字段为空或不是字符串")

    encoded = value.strip()

    # 同时兼容纯 Base64 和 data:image/jpeg;base64,... 格式。
    if encoded.startswith("data:") and "," in encoded:
        encoded = encoded.split(",", 1)[1]

    try:
        return base64.b64decode(encoded, validate=True)
    except binascii.Error:
        # 某些发送端可能包含换行或缺失严格填充。
        try:
            return base64.b64decode(encoded)
        except Exception as exc:
            raise ValueError(f"Base64 解码失败: {exc}") from exc


def save_compressed_jpeg(
    image_base64: str,
    output_path: Path,
) -> dict[str, Any]:
    raw = decode_base64_image(image_base64)

    try:
        with Image.open(io.BytesIO(raw)) as source:
            source.load()

            # 修复手机、摄像头图片可能携带的 EXIF 方向信息。
            image = ImageOps.exif_transpose(source)

            if image.mode != "RGB":
                image = image.convert("RGB")
            else:
                image = image.copy()

            original_width, original_height = image.size

            image.thumbnail(
                (MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT),
                Image.Resampling.LANCZOS,
            )

            output_width, output_height = image.size

            output_path.parent.mkdir(parents=True, exist_ok=True)

            temporary_path = output_path.with_suffix(
                output_path.suffix + ".tmp"
            )

            image.save(
                temporary_path,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
                progressive=True,
            )

            temporary_path.replace(output_path)

    except Exception as exc:
        raise ValueError(f"图片处理失败: {exc}") from exc

    return {
        "path": str(output_path),
        "filename": output_path.name,
        "originalWidth": original_width,
        "originalHeight": original_height,
        "width": output_width,
        "height": output_height,
        "sourceBytes": len(raw),
        "storedBytes": output_path.stat().st_size,
        "format": "JPEG",
        "quality": JPEG_QUALITY,
    }


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    temporary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    temporary_path.replace(path)


def relative_to_event_root(path: Path) -> str:
    return str(path.relative_to(EVENT_DIR))


def directory_size(path: Path) -> int:
    total = 0

    if not path.exists():
        return total

    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except FileNotFoundError:
            continue

    return total


class EventHandler(BaseHTTPRequestHandler):
    server_version = "VAEventReceiver/2.1"

    def send_json(self, status: int, data: Any) -> None:
        body = json.dumps(
            data,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(
                200,
                {
                    "status": "ok",
                    "service": "va-http-event-receiver",
                    "version": "2.1",
                    "eventDir": str(EVENT_DIR),
                    "storageBytes": directory_size(EVENT_DIR),
                },
            )
            return

        self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/events":
            self.send_json(404, {"error": "not found"})
            return

        event_directory: Path | None = None

        try:
            content_type = self.headers.get("Content-Type", "")
            if content_type and "application/json" not in content_type.lower():
                raise ValueError(
                    f"不支持的 Content-Type: {content_type}"
                )

            length_header = self.headers.get("Content-Length")
            if length_header is None:
                raise ValueError("缺少 Content-Length")

            length = int(length_header)

            if length <= 0:
                raise ValueError("请求体为空")

            if length > MAX_REQUEST_BYTES:
                self.send_json(
                    413,
                    {
                        "resCode": 0,
                        "resMsg": [
                            f"请求体超过限制: {length} > "
                            f"{MAX_REQUEST_BYTES}"
                        ],
                    },
                )
                return

            raw = self.rfile.read(length)

            if len(raw) != length:
                raise ValueError(
                    f"请求体读取不完整: {len(raw)} != {length}"
                )

            try:
                event = json.loads(raw.decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise ValueError(f"请求体不是 UTF-8: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON 解析失败: {exc}") from exc

            if not isinstance(event, dict):
                raise ValueError("事件 JSON 顶层必须是对象")

            message_id = str(
                event.get("messageId")
                or f"event-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
            )
            safe_id = safe_filename(message_id)

            event_time = parse_event_time(event.get("timestamp"))
            date_directory = event_time.strftime("%Y%m%d")

            event_directory = EVENT_DIR / date_directory / safe_id
            images_directory = event_directory / "images"

            if event_directory.exists():
                # 重试消息或重复 messageId 不覆盖已有事件。
                duplicate_suffix = datetime.now().strftime(
                    "duplicate-%H%M%S-%f"
                )
                event_directory = (
                    EVENT_DIR
                    / date_directory
                    / f"{safe_id}-{duplicate_suffix}"
                )
                images_directory = event_directory / "images"

            images_directory.mkdir(parents=True, exist_ok=False)

            image_results: dict[str, Any] = {}
            image_errors: dict[str, str] = {}

            for field_name, filename in IMAGE_FIELDS.items():
                image_value = event.get(field_name)

                if not image_value:
                    continue

                output_path = images_directory / filename

                try:
                    image_info = save_compressed_jpeg(
                        image_value,
                        output_path,
                    )
                    image_info["path"] = relative_to_event_root(
                        output_path
                    )
                    image_results[field_name] = image_info
                except Exception as exc:
                    image_errors[field_name] = str(exc)

            # 原始元数据保留，但移除大型 Base64 图片内容。
            source_metadata = {
                key: value
                for key, value in event.items()
                if key not in IMAGE_FIELDS
            }

            normalized_event = {
                "schemaVersion": "va-event-v2.1",
                "messageId": message_id,
                "receivedAt": datetime.now()
                .astimezone()
                .isoformat(),
                "eventTime": event_time.isoformat(),
                "timestamp": event.get("timestamp"),
                "device": {
                    "deviceId": event.get("devId"),
                    "videoChannelId": event.get(
                        "videoChannelId"
                    ),
                    "channelName": event.get("channelName"),
                },
                "task": {
                    "taskId": event.get("taskId"),
                    "algorithmCode": event.get(
                        "algorithmCode"
                    ),
                    "algorithmId": event.get(
                        "algorithmId"
                    ),
                    "algorithmName": event.get(
                        "algorithmName"
                    ),
                    "category": event.get("category"),
                },
                "area": {
                    "areaId": event.get("areaId"),
                    "areaName": event.get("areaName"),
                },
                "recordId": event.get("recordId"),
                "isRetryMessage": event.get(
                    "isRetryMessage",
                    False,
                ),
                "images": {
                    "original": image_results.get(
                        "orignalPicture"
                    ),
                    "annotated": image_results.get(
                        "fullPicture"
                    ),
                    "detected": image_results.get(
                        "detectedPicture"
                    ),
                },
                "imageErrors": image_errors,
                "sourceMetadata": source_metadata,
            }

            event_json_path = event_directory / "event.json"
            atomic_write_json(
                event_json_path,
                normalized_event,
            )

            summary = {
                "messageId": message_id,
                "timestamp": event.get("timestamp"),
                "eventTime": event_time.isoformat(),
                "deviceId": event.get("devId"),
                "videoChannelId": event.get(
                    "videoChannelId"
                ),
                "channelName": event.get("channelName"),
                "taskId": event.get("taskId"),
                "algorithmId": event.get("algorithmId"),
                "algorithmName": event.get(
                    "algorithmName"
                ),
                "areaId": event.get("areaId"),
                "areaName": event.get("areaName"),
                "category": event.get("category"),
                "recordId": event.get("recordId"),
                "isRetryMessage": event.get(
                    "isRetryMessage",
                    False,
                ),
                "eventFile": relative_to_event_root(
                    event_json_path
                ),
                "eventDirectory": relative_to_event_root(
                    event_directory
                ),
                "imagesSaved": len(image_results),
                "imageErrors": image_errors,
            }

            with JSONL_LOCK:
                with (EVENT_DIR / "events.jsonl").open(
                    "a",
                    encoding="utf-8",
                ) as file:
                    file.write(
                        json.dumps(
                            summary,
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

            stored_size = directory_size(event_directory)

            print(
                f"[EVENT] id={message_id} "
                f"channel={summary['channelName']} "
                f"algorithm={summary['algorithmName']} "
                f"images={len(image_results)} "
                f"errors={len(image_errors)} "
                f"stored={stored_size / 1024:.1f}KiB",
                flush=True,
            )

            self.send_json(
                200,
                {
                    "resCode": 1,
                    "resMsg": [],
                    "messageId": message_id,
                    "imagesSaved": len(image_results),
                },
            )

        except Exception as exc:
            # 如果事件处理中途失败，删除未完成目录，
            # 避免留下半成品文件。
            if event_directory is not None:
                shutil.rmtree(
                    event_directory,
                    ignore_errors=True,
                )

            print(
                f"[ERROR] {type(exc).__name__}: {exc}",
                flush=True,
            )

            self.send_json(
                400,
                {
                    "resCode": 0,
                    "resMsg": [str(exc)],
                },
            )

    def log_message(self, fmt: str, *args: Any) -> None:
        print(
            f"[HTTP] {self.client_address[0]} "
            f"{fmt % args}",
            flush=True,
        )


def main() -> None:
    address = (HOST, PORT)

    print(
        f"VA HTTP event receiver V2.1 listening on {address}",
        flush=True,
    )
    print(f"Event directory: {EVENT_DIR}", flush=True)
    print(
        f"JPEG quality: {JPEG_QUALITY}, "
        f"max image size: "
        f"{MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT}",
        flush=True,
    )
    print(
        f"Maximum request size: "
        f"{MAX_REQUEST_BYTES / 1024 / 1024:.1f} MiB",
        flush=True,
    )

    server = ThreadingHTTPServer(address, EventHandler)
    server.daemon_threads = True

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping receiver...", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
