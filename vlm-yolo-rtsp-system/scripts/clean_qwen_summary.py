#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path

try:
    from .event_utils import atomic_write_json
except ImportError:
    from event_utils import atomic_write_json

PROJECT_DIR = Path(__file__).resolve().parents[1]
EVENT_JSON_DIR = PROJECT_DIR / "outputs" / "event_json"


def clean_text(text: str) -> str:
    text = str(text or "")

    # 去掉 ANSI 控制字符
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)

    # 把一些终端特殊字符压掉
    text = text.replace("\r", "\n")

    # 优先寻找 Qwen 真正回答的开头
    start_markers = [
        "1. 场景摘要",
        "1．场景摘要",
        "场景摘要：",
        "场景摘要:",
    ]

    start = -1
    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            start = idx
            break

    if start != -1:
        text = text[start:]

    # 截断 Qwen 回答后面的性能统计和退出命令
    end_markers = [
        "[ Prompt:",
        "> /exit",
        "Exiting...",
        "Script done",
        "COMMAND_EXIT_CODE",
    ]

    cut_positions = []
    for marker in end_markers:
        idx = text.find(marker)
        if idx != -1:
            cut_positions.append(idx)

    if cut_positions:
        text = text[:min(cut_positions)]

    # 去掉多余空行和首尾空白
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            lines.append(line)

    return "\n".join(lines).strip()


def clean_event_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    raw = ""

    # 优先从 qwen_log_path 读取原始日志
    qwen_log_path = data.get("qwen_log_path", "")
    if qwen_log_path:
        log_path = Path(qwen_log_path)
        if log_path.exists():
            raw = log_path.read_text(encoding="utf-8", errors="ignore")

    # 如果没有日志文件，就从 qwen_summary 里清洗
    if not raw:
        raw = data.get("qwen_summary", "")

    cleaned = clean_text(raw)

    # 如果没有提取到真正摘要，就用风险字段兜底
    if not cleaned or "Script started" in cleaned or "Loading model" in cleaned:
        risk_reason = data.get("risk_reason", "")
        action = data.get("recommended_action", "")
        cleaned = f"风险判断：{risk_reason}\n处理建议：{action}".strip()

    data["qwen_summary"] = cleaned

    atomic_write_json(path, data)

    return cleaned


def main():
    files = sorted(EVENT_JSON_DIR.glob("event_*.json"))

    if not files:
        print("未找到 event_json 文件")
        return

    for path in files:
        cleaned = clean_event_json(path)
        print("=" * 80)
        print(path)
        print(cleaned[:300])

    print("=" * 80)
    print(f"清洗完成，共处理 {len(files)} 个事件 JSON")


if __name__ == "__main__":
    main()
