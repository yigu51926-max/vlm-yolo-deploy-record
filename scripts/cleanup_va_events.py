#!/usr/bin/env python3
"""清理过期或超容量的 VA HTTP 事件存储。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path


EVENT_DIR = Path(
    os.environ.get(
        "VA_EVENT_DIR",
        "/home/qi/va-test/http-events-v2",
    )
).expanduser().resolve()

# 设为 0 可关闭对应限制。
RETENTION_DAYS = int(
    os.environ.get("VA_EVENT_RETENTION_DAYS", "14")
)
MAX_STORAGE_BYTES = int(
    os.environ.get(
        "VA_MAX_STORAGE_BYTES",
        str(20 * 1024 * 1024 * 1024),
    )
)


def directory_size(directory: Path) -> int:
    total = 0

    for item in directory.rglob("*"):
        try:
            if item.is_file() and not item.is_symlink():
                total += item.stat().st_size
        except FileNotFoundError:
            continue

    return total


def get_event_directories() -> list[tuple[float, Path, int]]:
    events: list[tuple[float, Path, int]] = []

    for event_json in EVENT_DIR.rglob("event.json"):
        event_directory = event_json.parent

        try:
            events.append(
                (
                    event_json.stat().st_mtime,
                    event_directory,
                    directory_size(event_directory),
                )
            )
        except FileNotFoundError:
            continue

    return sorted(events, key=lambda item: item[0])


def prune_empty_parents(event_directory: Path) -> None:
    parent = event_directory.parent

    while parent != EVENT_DIR:
        try:
            parent.rmdir()
        except OSError:
            break

        parent = parent.parent


def rewrite_index(deleted_directories: set[str]) -> int:
    """同步删除 events.jsonl 中已被清除事件的索引。"""
    index_path = EVENT_DIR / "events.jsonl"

    if not deleted_directories or not index_path.exists():
        return 0

    kept_lines: list[str] = []
    removed = 0

    for line in index_path.read_text(
        encoding="utf-8"
    ).splitlines():
        try:
            summary = json.loads(line)
            event_directory = str(
                summary.get("eventDirectory", "")
            ).replace("\\", "/")

            if event_directory in deleted_directories:
                removed += 1
                continue
        except json.JSONDecodeError:
            # 损坏的旧行不自动删除，避免额外丢失数据。
            pass

        kept_lines.append(line)

    if removed > 0:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=EVENT_DIR,
            prefix=".events.jsonl.",
            delete=False,
        ) as temporary:
            temporary.write("\n".join(kept_lines))

            if kept_lines:
                temporary.write("\n")

            temporary_path = Path(temporary.name)

        temporary_path.replace(index_path)

    return removed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示将被清理的事件，不实际删除。",
    )
    args = parser.parse_args()

    if not EVENT_DIR.is_dir():
        print(f"[CLEANUP] 事件目录不存在：{EVENT_DIR}")
        return 0

    cutoff = time.time() - RETENTION_DAYS * 24 * 60 * 60
    total_size = directory_size(EVENT_DIR)
    deleted_directories: set[str] = set()
    deleted_count = 0
    freed_bytes = 0

    for modified_time, event_directory, event_size in (
        get_event_directories()
    ):
        expired = (
            RETENTION_DAYS > 0
            and modified_time < cutoff
        )
        over_limit = (
            MAX_STORAGE_BYTES > 0
            and total_size > MAX_STORAGE_BYTES
        )

        if not expired and not over_limit:
            continue

        relative_directory = event_directory.relative_to(
            EVENT_DIR
        ).as_posix()
        reason = "expired" if expired else "over-limit"

        if args.dry_run:
            print(
                f"[DRY-RUN] {reason}: {relative_directory} "
                f"({event_size / 1024 / 1024:.1f} MiB)"
            )
            total_size = max(0, total_size - event_size)
            continue

        try:
            shutil.rmtree(event_directory)
        except FileNotFoundError:
            continue

        deleted_directories.add(relative_directory)
        deleted_count += 1
        freed_bytes += event_size
        total_size = max(0, total_size - event_size)
        prune_empty_parents(event_directory)

    index_removed = 0

    if not args.dry_run:
        index_removed = rewrite_index(deleted_directories)

    print(
        "[CLEANUP] "
        f"deleted={deleted_count} "
        f"freed={freed_bytes / 1024 / 1024:.1f}MiB "
        f"indexRemoved={index_removed} "
        f"remaining={directory_size(EVENT_DIR) / 1024 / 1024:.1f}MiB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
