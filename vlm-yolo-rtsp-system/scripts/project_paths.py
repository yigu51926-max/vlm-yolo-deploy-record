import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_project_path(value: str | Path, env_var: str | None = None) -> Path:
    raw_value = os.environ.get(env_var, str(value)) if env_var else str(value)
    path = Path(os.path.expandvars(raw_value)).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def resolve_config_paths(config: dict[str, Any]) -> dict[str, Any]:
    config["yolo"]["model_path"] = str(
        resolve_project_path(config["yolo"]["model_path"], "YOLO_MODEL_PATH")
    )

    qwen = config["qwen"]
    qwen["llama_cli"] = str(
        resolve_project_path(qwen["llama_cli"], "LLAMA_CLI_PATH")
    )
    qwen["model_path"] = str(
        resolve_project_path(qwen["model_path"], "QWEN_MODEL_PATH")
    )
    qwen["mmproj_path"] = str(
        resolve_project_path(qwen["mmproj_path"], "QWEN_MMPROJ_PATH")
    )

    outputs = config["outputs"]
    outputs["keyframe_dir"] = str(
        resolve_project_path(outputs["keyframe_dir"], "KEYFRAME_DIR")
    )
    outputs["event_log_dir"] = str(
        resolve_project_path(outputs["event_log_dir"], "EVENT_LOG_DIR")
    )
    outputs["event_json_dir"] = str(
        resolve_project_path(outputs["event_json_dir"], "EVENT_JSON_DIR")
    )
    return config
