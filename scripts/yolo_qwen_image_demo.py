import os
from pathlib import Path
import cv2
import subprocess
from ultralytics import YOLO

# ===== 路径配置 =====
PROJECT_ROOT = Path(__file__).resolve().parents[1] / "vlm-yolo-rtsp-system"
IMAGE_PATH = Path(os.environ.get("TEST_IMAGE_PATH", PROJECT_ROOT / "assets" / "a.png"))
YOLO_MODEL = Path(os.environ.get("YOLO_MODEL_PATH", PROJECT_ROOT / "models" / "yolo26n.pt"))
LLAMA_CLI = Path(os.environ.get("LLAMA_CLI_PATH", PROJECT_ROOT / "vendor" / "llama.cpp" / "build" / "bin" / "llama-cli"))
QWEN_MODEL = Path(os.environ.get("QWEN_MODEL_PATH", PROJECT_ROOT / "models" / "qwen" / "Qwen3VL-2B-Instruct-Q4_K_M.gguf"))
MMPROJ = Path(os.environ.get("QWEN_MMPROJ_PATH", PROJECT_ROOT / "models" / "qwen" / "mmproj-Qwen3VL-2B-Instruct-F16.gguf"))
OUTPUT_IMAGE = PROJECT_ROOT / "outputs" / "yolo_qwen_result.jpg"


def run_yolo():
    model = YOLO(str(YOLO_MODEL))
    results = model.predict(
        source=str(IMAGE_PATH),
        conf=0.25,
        imgsz=960,
        verbose=True
    )

    r = results[0]
    names = r.names

    img = cv2.imread(str(IMAGE_PATH))
    if img is None:
        raise RuntimeError(f"图片读取失败：{IMAGE_PATH}")

    yolo_lines = []

    if r.boxes is None or len(r.boxes) == 0:
        yolo_summary = "YOLO26 未检测到明确目标。"
    else:
        for i, box in enumerate(r.boxes):
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            label = names[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            yolo_lines.append(
                f"目标{i}: 类别={label}, 置信度={conf:.2f}, 位置=({x1},{y1},{x2},{y2})"
            )

            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                img,
                f"{label} {conf:.2f}",
                (x1, max(20, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        yolo_summary = "\n".join(yolo_lines)

    OUTPUT_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUTPUT_IMAGE), img)

    return yolo_summary


def run_qwen(yolo_summary):
    prompt = f"""
你是一个视觉语言多模态安全分析助手。

YOLO26 已经对图片进行了目标检测，检测结果如下：
{yolo_summary}

请结合整张图片和 YOLO 检测结果，用中文完成以下分析：
1. 图片中主要有哪些目标？
2. YOLO26 的检测结果是否合理？
3. 人和车辆之间是否存在潜在风险？
4. 如果这是道路监控、机器人巡检或工业安全场景，应该给出什么安全提醒？
5. 请给出一句简洁的报警/提示语。

要求：回答清晰、分点说明，不要重复废话。
"""

    cmd = [
        str(LLAMA_CLI),
        "-m", str(QWEN_MODEL),
        "--mmproj", str(MMPROJ),
        "--image", str(IMAGE_PATH),
        "-p", prompt,
        "-n", "512",
    ]

    result = subprocess.run(
        cmd,
        input="/exit\\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    return result.stdout


def main():
    print("=" * 80)
    print("[1] 开始 YOLO26 目标检测")
    yolo_summary = run_yolo()

    print("=" * 80)
    print("[YOLO26 检测结果]")
    print(yolo_summary)

    print("=" * 80)
    print(f"[检测结果图已保存] {OUTPUT_IMAGE}")

    print("=" * 80)
    print("[2] 开始 Qwen3-VL 综合分析")
    qwen_answer = run_qwen(yolo_summary)

    print("=" * 80)
    print("[Qwen3-VL 分析结果]")
    print(qwen_answer)


if __name__ == "__main__":
    main()
