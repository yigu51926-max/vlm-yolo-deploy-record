import os
import json
import shlex
import argparse
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from .project_paths import PROJECT_ROOT, resolve_config_paths, resolve_project_path
except ImportError:
    from project_paths import PROJECT_ROOT, resolve_config_paths, resolve_project_path


def load_config(config_path: str):
    path = resolve_project_path(config_path)
    with path.open("r", encoding="utf-8") as f:
        return resolve_config_paths(json.load(f))


def build_prompt(config, detect_info: str = ""):
    prompt = config["qwen"]["prompt"]

    if detect_info:
        prompt += "\n\n以下是 YOLO26 的检测结果，请结合检测结果进行分析：\n"
        prompt += detect_info

    return prompt


def make_log_path(config, image_path: str):
    log_dir = Path(config["outputs"]["event_log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_name = Path(image_path).stem
    return log_dir / f"qwen_analysis_{image_name}_{timestamp}.txt"


def check_file(path: str, name: str):
    if not Path(path).exists():
        raise FileNotFoundError(f"找不到{name}：{path}")


def run_qwen_analysis(config, image_path: str, detect_info: str = ""):
    qwen_cfg = config["qwen"]

    llama_cli = qwen_cfg["llama_cli"]
    model_path = qwen_cfg["model_path"]
    mmproj_path = qwen_cfg["mmproj_path"]

    image_path = str(resolve_project_path(image_path))
    check_file(image_path, "图片文件")
    check_file(llama_cli, "llama-cli")
    check_file(model_path, "Qwen 模型")
    check_file(mmproj_path, "mmproj 文件")

    prompt = build_prompt(config, detect_info)
    log_path = make_log_path(config, image_path)

    print("=" * 80)
    print("[Qwen3-VL] 开始分析图片")
    print(f"[图片] {image_path}")
    print(f"[日志] {log_path}")
    print("=" * 80)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".txt") as pf:
        pf.write(prompt)
        prompt_file = Path(pf.name)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".sh") as sf:
        runner_path = Path(sf.name)
        sf.write("#!/bin/bash\n")
        sf.write(f"{shlex.quote(llama_cli)} \\\n")
        sf.write(f"  -m {shlex.quote(model_path)} \\\n")
        sf.write(f"  --mmproj {shlex.quote(mmproj_path)} \\\n")
        sf.write(f"  --image {shlex.quote(image_path)} \\\n")
        sf.write(f"  -p \"$(cat {shlex.quote(str(prompt_file))})\" << 'EOF'\n")
        sf.write("/exit\n")
        sf.write("EOF\n")

    runner_path.chmod(0o755)

    # 使用 script 命令捕获 llama-cli 的交互式终端输出
    cmd = [
        "script",
        "-q",
        "-f",
        "-c",
        f"bash {shlex.quote(str(runner_path))}",
        str(log_path)
    ]

    process = subprocess.run(cmd, timeout=300, cwd=PROJECT_ROOT)

    prompt_file.unlink()
    runner_path.unlink()

    print("=" * 80)
    print("[Qwen3-VL] 分析完成")
    print(f"[returncode] {process.returncode}")
    print(f"[日志保存] {log_path}")
    print(f"[日志大小] {log_path.stat().st_size} bytes")
    print("=" * 80)

    return str(log_path)


def main():
    parser = argparse.ArgumentParser(description="Qwen3-VL 图片语义分析脚本")
    parser.add_argument("--config", default="configs/collaboration_config.json")
    parser.add_argument("--image", required=True, help="输入图片路径")
    parser.add_argument("--detect-info", default="", help="YOLO 检测结果文本")
    args = parser.parse_args()

    config = load_config(args.config)

    log_path = run_qwen_analysis(
        config=config,
        image_path=args.image,
        detect_info=args.detect_info
    )

    print("[日志预览]")
    os.system(f"tail -n 40 {shlex.quote(log_path)}")


if __name__ == "__main__":
    main()
