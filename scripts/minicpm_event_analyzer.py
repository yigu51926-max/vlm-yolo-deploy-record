#!/usr/bin/env python3
"""Analyze Receiver events with the local MiniCPM-V OpenAI-compatible API."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RECEIVER_URL = "http://127.0.0.1:18090"
DEFAULT_VLM_URL = "http://127.0.0.1:18091"
DEFAULT_EVENT_DIR = "/home/qi/va-test/http-events-v2"
DEFAULT_MODEL = "/models/MiniCPM-V-4.6"
OUTPUT_FILENAME = "minicpm-v-4.6.json"


class AnalyzerError(RuntimeError):
    """An expected, user-readable analyzer failure."""


def http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 180.0,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AnalyzerError(f"HTTP {exc.code} from {url}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise AnalyzerError(f"Cannot connect to {url}: {exc.reason}") from exc

    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AnalyzerError(f"Invalid JSON returned by {url}") from exc
    if not isinstance(result, dict):
        raise AnalyzerError(f"Expected a JSON object from {url}")
    return result


def http_bytes(url: str, *, timeout: float = 60.0) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"Accept": "image/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AnalyzerError(f"HTTP {exc.code} from {url}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise AnalyzerError(f"Cannot download event image: {exc.reason}") from exc


def select_event(
    events: list[dict[str, Any]],
    *,
    message_id: str | None,
    latest: bool,
) -> dict[str, Any]:
    if not events:
        raise AnalyzerError("Receiver returned no events")

    if message_id is not None:
        for event in events:
            if str(event.get("messageId", "")) == message_id:
                return event
        raise AnalyzerError(f"Event not found: {message_id}")

    if not latest:
        raise AnalyzerError("Choose --message-id or --latest")

    def sort_key(event: dict[str, Any]) -> tuple[int, str]:
        timestamp = str(event.get("timestamp", ""))
        try:
            numeric = int(timestamp)
        except ValueError:
            numeric = -1
        return numeric, str(event.get("eventTime", ""))

    return max(events, key=sort_key)


def _find_images_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        images = value.get("images")
        if isinstance(images, dict):
            return images
        for child in value.values():
            found = _find_images_mapping(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_images_mapping(child)
            if found is not None:
                return found
    return None


def _entry_path(entry: Any, event_directory: str) -> str | None:
    if isinstance(entry, str) and entry.strip():
        return entry.strip()
    if not isinstance(entry, dict):
        return None

    for key in ("path", "relativePath", "relative_path"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    filename = entry.get("filename") or entry.get("fileName") or entry.get("name")
    if isinstance(filename, str) and filename.strip() and event_directory:
        return f"{event_directory.rstrip('/')}/images/{filename.strip()}"
    return None


def select_image_path(detail: dict[str, Any], index_event: dict[str, Any]) -> str:
    """Prefer annotated, then original, then detected event imagery."""
    event_directory = str(index_event.get("eventDirectory", "")).strip("/")
    images = _find_images_mapping(detail) or {}

    for kind in ("annotated", "original", "detected"):
        path = _entry_path(images.get(kind), event_directory)
        if path:
            return path.lstrip("/")

    if event_directory:
        # Receiver V2 uses this deterministic layout.
        return f"{event_directory}/images/annotated.jpg"
    raise AnalyzerError("Event detail does not contain a usable image path")


def extract_message_content(response: dict[str, Any]) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AnalyzerError("VLM response is missing choices[0].message.content") from exc

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return "\n".join(parts).strip()
    raise AnalyzerError("VLM response content is not text")



def _repair_unquoted_chinese_value(text: str) -> str:
    """
    Repair simple JSON values without quotes.
    Example:
        {"summary": 交通场景检测}
    becomes:
        {"summary": "交通场景检测"}
    """
    pattern = r'(:\s*)([\u4e00-\u9fff][^,\}\]]*)'

    def repl(match: re.Match[str]) -> str:
        return f'{match.group(1)}"{match.group(2).strip()}"'

    return re.sub(pattern, repl, text)


def _extract_json_fragments(text: str) -> list[str]:
    fragments = []
    depth = 0
    start = None

    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1

        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                fragments.append(text[start:i + 1])
                start = None

    return fragments


def parse_model_json(content: str) -> dict[str, Any]:
    candidate = content.strip()

    fenced = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        candidate,
        flags=re.S | re.I,
    )

    if fenced:
        candidate = fenced.group(1).strip()

    # 先尝试标准 JSON
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 提取多个 JSON 片段
    fragments = _extract_json_fragments(candidate)

    if not fragments:
        raise AnalyzerError(
            "Model output does not contain JSON fragments"
        )

    result = {}

    for fragment in fragments:
        repaired = _repair_unquoted_chinese_value(fragment)

        try:
            obj = json.loads(repaired)
        except json.JSONDecodeError:
            continue

        if isinstance(obj, dict):
            result.update(obj)

    if not result:
        raise AnalyzerError(
            "Model output contains invalid JSON fragments"
        )

    return result


def build_prompt(event: dict[str, Any]) -> str:
    context = {
        key: event.get(key)
        for key in (
            "eventTime",
            "deviceId",
            "channelName",
            "algorithmName",
            "areaName",
            "category",
        )
        if event.get(key) is not None
    }
    return (
        "你是交通事件图像分析器。请分析图片，并只输出一个合法 JSON 对象，"
        "禁止 Markdown、代码块和额外说明。必须包含以下字段："
        '"summary"（简短中文总结）、"visibleFacts"（仅图片中可直接确认的事实数组）、'
        '"vehicleTypes"（可见车辆类型数组）、"roadScene"（道路场景描述）、'
        '"risks"（风险数组；每项含 description、basis、certainty）、'
        '"riskLevel"（low/medium/high）、"confidence"（0 到 1 的数值）。'
        "严格区分可见事实和推断：不确定就明确写不确定，不得虚构碰撞、违章、车速、"
        "人员身份或图片中不可见的信息。事件元数据仅作上下文，不得覆盖图片证据。"
        f"事件上下文：{json.dumps(context, ensure_ascii=False)}"
    )


def guess_mime(path: str, response_mime: str, data: bytes) -> str:
    if response_mime.startswith("image/"):
        return response_mime
    guessed = mimetypes.guess_type(path)[0]
    if guessed and guessed.startswith("image/"):
        return guessed
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return "application/octet-stream"


def make_vlm_payload(
    *,
    model: str,
    prompt: str,
    image_data: bytes,
    mime_type: str,
    max_tokens: int,
) -> dict[str, Any]:
    encoded = base64.b64encode(image_data).decode("ascii")
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
        # MiniCPM-V 4.6 workaround for the Transformers server's multi-slice
        # shape error on common 1280x720 Receiver images.
        "chat_template_kwargs": {
            "downsample_mode": "16x",
            "max_slice_nums": 1,
        },
    }


def safe_event_directory(event_root: Path, index_event: dict[str, Any]) -> Path:
    relative = str(index_event.get("eventDirectory", "")).strip()
    if not relative:
        raise AnalyzerError("Event index is missing eventDirectory")
    root = event_root.expanduser().resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise AnalyzerError("Unsafe eventDirectory in event index") from exc
    return target


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def analyze(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    receiver_url = args.receiver_url.rstrip("/")
    vlm_url = args.vlm_url.rstrip("/")

    listing = http_json(f"{receiver_url}/events", timeout=args.timeout)
    events = listing.get("events")
    if not isinstance(events, list) or not all(isinstance(item, dict) for item in events):
        raise AnalyzerError("Receiver /events response has no valid events array")
    index_event = select_event(events, message_id=args.message_id, latest=args.latest)
    message_id = str(index_event.get("messageId", "")).strip()
    if not message_id:
        raise AnalyzerError("Selected event is missing messageId")

    detail_url = f"{receiver_url}/events/{urllib.parse.quote(message_id, safe='')}"
    detail = http_json(detail_url, timeout=args.timeout)
    image_path = select_image_path(detail, index_event)
    encoded_path = urllib.parse.quote(image_path, safe="/")
    image_data, response_mime = http_bytes(
        f"{receiver_url}/images/{encoded_path}", timeout=args.timeout
    )
    if not image_data:
        raise AnalyzerError("Receiver returned an empty image")

    mime_type = guess_mime(image_path, response_mime, image_data)
    payload = make_vlm_payload(
        model=args.model,
        prompt=build_prompt(index_event),
        image_data=image_data,
        mime_type=mime_type,
        max_tokens=args.max_tokens,
    )
    vlm_response = http_json(
        f"{vlm_url}/v1/chat/completions",
        method="POST",
        payload=payload,
        timeout=args.vlm_timeout,
    )
    raw_content = extract_message_content(vlm_response)

    analyzed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    base_result: dict[str, Any] = {
        "messageId": message_id,
        "model": args.model,
        "analyzedAt": analyzed_at,
        "sourceImage": image_path,
    }
    try:
        model_result = parse_model_json(raw_content)
    except AnalyzerError as exc:
        result = {
            **base_result,
            "status": "parse_error",
            "error": str(exc),
            "rawResponse": raw_content,
        }
    else:
        result = {**model_result, **base_result, "status": "ok"}
        usage = vlm_response.get("usage")
        if isinstance(usage, dict):
            result["usage"] = usage

    output_path = safe_event_directory(Path(args.event_dir), index_event) / "analysis" / OUTPUT_FILENAME
    if output_path.exists() and not args.overwrite:
        raise AnalyzerError(f"Output already exists; use --overwrite: {output_path}")
    atomic_write_json(output_path, result)
    return output_path, result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze one HTTP Event Receiver event with MiniCPM-V 4.6"
    )
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--message-id", help="analyze the specified Receiver messageId")
    choice.add_argument("--latest", action="store_true", help="analyze the newest indexed event")
    parser.add_argument(
        "--receiver-url",
        default=os.environ.get("VA_RECEIVER_URL", DEFAULT_RECEIVER_URL),
    )
    parser.add_argument(
        "--vlm-url",
        default=os.environ.get("VA_VLM_URL", DEFAULT_VLM_URL),
    )
    parser.add_argument(
        "--event-dir",
        default=os.environ.get("VA_EVENT_DIR", DEFAULT_EVENT_DIR),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("VA_VLM_MODEL", DEFAULT_MODEL),
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--vlm-timeout", type=float, default=300.0)
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        output_path, result = analyze(args)
    except AnalyzerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("ERROR: interrupted", file=sys.stderr)
        return 130

    print(json.dumps({"output": str(output_path), "status": result["status"]}, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
