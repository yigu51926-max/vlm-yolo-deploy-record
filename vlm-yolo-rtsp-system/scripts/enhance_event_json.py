import os
import re
import json
import glob
import argparse


def remove_control_chars(text):
    # 去掉 ANSI 颜色码和大部分终端控制字符
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    text = text.replace("\b", "")
    text = text.replace("\r", "\n")
    return text


def clean_qwen_log(text):
    """
    从 llama-cli/script 终端日志中尽量提取 Qwen 真正生成的中文分析内容。
    """
    text = remove_control_chars(text)

    # 去掉明显的终端尾巴
    cut_markers = [
        "[ Prompt:",
        "Exiting...",
        "Script done",
        "> /exit",
        "> /"
    ]

    for marker in cut_markers:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]

    # 优先从真正的 markdown 标题开始截取，避免截到 prompt 里的“安全场景分析”
    candidates = [
        "### 安全场景分析",
        "## 安全场景分析",
        "# 安全场景分析",
        "安全场景分析"
    ]

    start_idx = -1
    for marker in candidates:
        idx = text.rfind(marker)
        if idx != -1:
            start_idx = idx
            break

    if start_idx != -1:
        text = text[start_idx:]

    remove_keywords = [
        "llama",
        "build:",
        "main:",
        "system_info:",
        "sampling:",
        "generate:",
        "model_loader:",
        "print_info:",
        "load_tensors:",
        "llm_load",
        "common_init",
        "chat_template",
        "YOLO检测结果：",
        "以下是 YOLO26",
        "请根据图片内容",
        "重点说明画面中",
        "请结合检测结果"
    ]

    lines = []
    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if any(k in line for k in remove_keywords):
            continue

        # 去掉残留的转圈/进度噪声
        if re.fullmatch(r"[|/\\\-\s]+", line):
            continue

        lines.append(line)

    cleaned = "\n".join(lines).strip()

    # 去掉过长连续重复内容
    cleaned = re.sub(r"(.{10,80})\1{2,}", r"\1", cleaned)

    return cleaned


def count_objects(detected_objects):
    counts = {}
    for obj in detected_objects:
        name = obj.get("class_name", "")
        counts[name] = counts.get(name, 0) + 1
    return counts


def build_summary_from_qwen(qwen_text, detected_objects):
    counts = count_objects(detected_objects)
    has_person = counts.get("person", 0) > 0
    has_vehicle = any(counts.get(x, 0) > 0 for x in ["car", "truck", "bus", "motorcycle"])

    if has_person and has_vehicle:
        risk_level = "warning"
        risk_reason = "检测到行人与车辆同时出现在画面中，存在人车混行或交通冲突风险。"
        recommended_action = "建议后台系统标记为需要关注事件，并持续跟踪行人与车辆的位置变化。"
    elif has_person:
        risk_level = "normal"
        risk_reason = "检测到人员目标，但未发现明显车辆或高风险目标组合。"
        recommended_action = "建议保留事件记录，并根据后续连续帧判断人员行为是否异常。"
    else:
        risk_level = "normal"
        risk_reason = "未检测到达到触发条件的高风险目标组合。"
        recommended_action = "建议作为普通事件归档。"

    # 优先从“综合判断”部分取摘要
    qwen_summary = ""

    if qwen_text:
        summary_text = qwen_text

        for marker in ["### 综合判断", "## 综合判断", "综合判断", "综上所述"]:
            idx = qwen_text.find(marker)
            if idx != -1:
                summary_text = qwen_text[idx:]
                break

        summary_text = re.sub(r"[#*\-`>]", "", summary_text)
        summary_text = re.sub(r"\s+", " ", summary_text).strip()

        sentences = re.split(r"[。！？]", summary_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) >= 8]

        if sentences:
            qwen_summary = "。".join(sentences[:2]) + "。"

    if not qwen_summary:
        qwen_summary = risk_reason

    # 控制摘要长度，方便后台展示
    if len(qwen_summary) > 260:
        qwen_summary = qwen_summary[:260] + "……"

    return risk_level, risk_reason, recommended_action, qwen_summary


def enhance_one_event(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    qwen_log_path = event.get("qwen_log_path", "")
    detected_objects = event.get("detected_objects", [])

    qwen_text = ""

    if qwen_log_path and os.path.exists(qwen_log_path):
        with open(qwen_log_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()
        qwen_text = clean_qwen_log(raw_text)

    risk_level, risk_reason, recommended_action, qwen_summary = build_summary_from_qwen(
        qwen_text=qwen_text,
        detected_objects=detected_objects
    )

    event["risk_level"] = risk_level
    event["risk_reason"] = risk_reason
    event["recommended_action"] = recommended_action
    event["qwen_summary"] = qwen_summary
    event["qwen_analysis_cleaned"] = qwen_text[:1500]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(event, f, ensure_ascii=False, indent=2)

    return json_path


def main():
    parser = argparse.ArgumentParser(description="增强 YOLO + Qwen 事件 JSON，加入摘要、风险原因和建议动作")
    parser.add_argument("--event-json-dir", default="outputs/event_json")
    args = parser.parse_args()

    json_files = sorted(glob.glob(os.path.join(args.event_json_dir, "event_*.json")))

    if not json_files:
        print(f"未找到事件 JSON：{args.event_json_dir}")
        return

    print(f"找到 {len(json_files)} 个事件 JSON")

    for path in json_files:
        enhanced_path = enhance_one_event(path)
        print(f"已增强：{enhanced_path}")

    print("全部事件 JSON 增强完成")


if __name__ == "__main__":
    main()
