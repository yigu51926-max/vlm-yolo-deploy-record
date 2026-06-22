#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import html
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).resolve().parents[1]
EVENT_DIR = PROJECT_DIR / "outputs" / "event_json"
DASHBOARD_DIR = PROJECT_DIR / "outputs" / "dashboard"
HTML_PATH = DASHBOARD_DIR / "index.html"


def esc(value):
    if value is None:
        return ""
    return html.escape(str(value))


def image_path(keyframe_path):
    if not keyframe_path:
        return ""
    return "../keyframes/" + Path(keyframe_path).name


def load_events():
    events = []
    for path in sorted(EVENT_DIR.glob("event_*.json")):
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        data["_json_name"] = path.name
        events.append(data)
    return events


def card(event):
    event_id = esc(event.get("event_id", "unknown"))
    stream_name = esc(event.get("stream_name", "unknown"))
    risk_level = esc(event.get("risk_level", "unknown"))
    risk_reason = esc(event.get("risk_reason", ""))
    recommended_action = esc(event.get("recommended_action", ""))
    qwen_summary = esc(event.get("qwen_summary", ""))
    trigger_reason = esc(event.get("trigger_reason", ""))
    json_name = esc(event.get("_json_name", ""))
    img = image_path(event.get("keyframe_path", ""))

    if img:
        img_html = f'<img src="{esc(img)}" alt="{event_id}">'
    else:
        img_html = '<div class="no-img">无关键帧</div>'

    return f"""
    <div class="card">
      <div class="top">
        <div>
          <h2>{event_id}</h2>
          <p class="meta">视频流：{stream_name} ｜ JSON：{json_name}</p>
        </div>
        <span class="badge">{risk_level}</span>
      </div>

      <div class="image-box">
        {img_html}
      </div>

      <div class="section">
        <b>触发原因：</b>
        <p>{trigger_reason}</p>
      </div>

      <div class="section">
        <b>Qwen 摘要：</b>
        <p>{qwen_summary}</p>
      </div>

      <div class="section">
        <b>风险原因：</b>
        <p>{risk_reason}</p>
      </div>

      <div class="section">
        <b>处理建议：</b>
        <p>{recommended_action}</p>
      </div>
    </div>
    """


def main():
    events = load_events()
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    cards = "\n".join(card(e) for e in events)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_text = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>YOLO26 + Qwen3-VL 事件看板</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, "Microsoft YaHei", sans-serif;
      background: #f3f4f6;
      color: #111827;
    }}
    header {{
      background: #111827;
      color: white;
      padding: 24px 36px;
    }}
    header h1 {{
      margin: 0;
      font-size: 28px;
    }}
    header p {{
      margin: 8px 0 0 0;
      color: #d1d5db;
    }}
    .summary {{
      padding: 20px 36px 0 36px;
      font-size: 18px;
    }}
    main {{
      padding: 24px 36px 48px 36px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 24px;
    }}
    .card {{
      background: white;
      border-radius: 16px;
      padding: 20px;
      box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    }}
    .top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
    }}
    h2 {{
      margin: 0;
    }}
    .meta {{
      color: #6b7280;
      font-size: 14px;
      margin-top: 6px;
    }}
    .badge {{
      background: #d97706;
      color: white;
      border-radius: 999px;
      padding: 6px 12px;
      font-weight: bold;
      white-space: nowrap;
    }}
    .image-box {{
      margin: 16px 0;
      background: #0f172a;
      border-radius: 12px;
      overflow: hidden;
      text-align: center;
    }}
    .image-box img {{
      width: 100%;
      display: block;
    }}
    .no-img {{
      color: #cbd5e1;
      padding: 50px;
    }}
    .section {{
      background: #f9fafb;
      border-radius: 10px;
      padding: 12px;
      margin-top: 10px;
    }}
    .section p {{
      margin: 6px 0 0 0;
      line-height: 1.6;
    }}
  </style>
</head>
<body>
  <header>
    <h1>YOLO26 + Qwen3-VL 事件看板</h1>
    <p>生成时间：{now} ｜ 数据来源：outputs/event_json</p>
  </header>

  <div class="summary">
    当前事件数量：<b>{len(events)}</b>
  </div>

  <main>
    {cards}
  </main>
</body>
</html>
"""

    HTML_PATH.write_text(html_text, encoding="utf-8")
    print("后台事件看板生成完成")
    print("事件数量:", len(events))
    print("输出文件:", HTML_PATH)


if __name__ == "__main__":
    main()
