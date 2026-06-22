import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_RISK_LEVELS = {"high", "warning", "normal", "unknown"}
RISK_LEVEL_ALIASES = {
    "danger": "high",
    "medium": "warning",
    "low": "normal",
    "safe": "normal",
}


def generate_event_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"event_{timestamp}_{uuid.uuid4().hex[:8]}"


def normalize_risk_level(value: Any) -> str:
    level = str(value or "").strip().lower()
    level = RISK_LEVEL_ALIASES.get(level, level)
    return level if level in VALID_RISK_LEVELS else "unknown"


def atomic_write_json(path: str | Path, data: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(data, temp_file, ensure_ascii=False, indent=2)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, target)
        temp_path = None
        return target
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
