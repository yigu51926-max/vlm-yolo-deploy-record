#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

try:
    from scripts.event_utils import normalize_risk_level
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.event_utils import normalize_risk_level


PROJECT_DIR = Path(__file__).resolve().parents[1]
EVENT_DIR = PROJECT_DIR / "outputs" / "event_json"
KEYFRAME_DIR = PROJECT_DIR / "outputs" / "keyframes"
LOGGER = logging.getLogger(__name__)

app = FastAPI(title="YOLO26 + Qwen3-VL Event Dashboard")
app.mount(
    "/keyframes",
    StaticFiles(directory=str(KEYFRAME_DIR), check_dir=False),
    name="keyframes",
)


def clean_qwen_text(text: Any) -> str:
    text = str(text or "")
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    text = text.replace("\r", "\n")

    start_markers = [
        "1. 场景摘要",
        "1.场景摘要",
        "场景摘要：",
        "场景摘要:",
        "1. 鍦烘櫙鎽樿",
        "1锛庡満鏅憳瑕",
        "鍦烘櫙鎽樿锛",
        "鍦烘櫙鎽樿:",
    ]

    start = -1
    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            start = idx
            break

    if start != -1:
        text = text[start:]

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
        text = text[: min(cut_positions)]

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            lines.append(line)

    return "\n".join(lines).strip()


def first_value(data: dict[str, Any], names: list[str], default: str = "") -> Any:
    for name in names:
        value = data.get(name)
        if value is not None and value != "":
            return value
    return default


def keyframe_url(keyframe_path: Any) -> str:
    if not keyframe_path:
        return ""
    return "/keyframes/" + Path(str(keyframe_path)).name


def normalize_event(data: dict[str, Any], json_path: Path) -> dict[str, Any]:
    json_mtime = json_path.stat().st_mtime
    timestamp = first_value(data, ["timestamp", "time", "created_at", "event_time"])
    if not timestamp:
        timestamp = datetime.fromtimestamp(json_mtime).strftime("%Y-%m-%d %H:%M:%S")

    qwen_summary = clean_qwen_text(
        first_value(data, ["qwen_summary", "qwen_result", "summary", "description"])
    )
    risk_reason = first_value(data, ["risk_reason", "reason", "risk_description"])
    recommended_action = first_value(
        data, ["recommended_action", "action", "suggestion", "handling_suggestion"]
    )

    if not qwen_summary or "Script started" in qwen_summary or "Loading model" in qwen_summary:
        fallback_lines = []
        if risk_reason:
            fallback_lines.append(f"风险判断：{risk_reason}")
        if recommended_action:
            fallback_lines.append(f"处理建议：{recommended_action}")
        qwen_summary = "\n".join(fallback_lines)

    return {
        "event_id": first_value(data, ["event_id", "id", "event_no"], "unknown"),
        "stream_name": first_value(data, ["stream_name", "camera_name", "source"], "unknown"),
        "risk_level": normalize_risk_level(first_value(data, ["risk_level", "level", "risk"], "unknown")),
        "qwen_summary": qwen_summary,
        "risk_reason": risk_reason,
        "recommended_action": recommended_action,
        "trigger_reason": first_value(data, ["trigger_reason", "trigger", "trigger_desc"]),
        "timestamp": timestamp,
        "json_name": json_path.name,
        "json_mtime": json_mtime,
        "keyframe_url": keyframe_url(
            first_value(data, ["keyframe_path", "keyframe", "image_path", "frame_path"])
        ),
    }


def load_events() -> list[dict[str, Any]]:
    if not EVENT_DIR.exists():
        return []

    events = []
    for path in EVENT_DIR.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                LOGGER.warning("跳过非对象事件文件 %s", path.name)
                continue

            events.append(normalize_event(data, path))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("跳过异常事件文件 %s: %s", path.name, exc)
            continue

    events.sort(key=lambda event: event["json_mtime"], reverse=True)
    return events


@app.get("/api/events")
def api_events() -> dict[str, Any]:
    events = load_events()
    return {"count": len(events), "events": events}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>后台事件看板 v0.4</title>
  <style>
    body {
      margin: 0;
      font-family: Arial, "Microsoft YaHei", sans-serif;
      background: #f3f4f6;
      color: #111827;
    }
    header {
      background: #111827;
      color: white;
      padding: 24px 36px;
    }
    header h1 {
      margin: 0;
      font-size: 28px;
    }
    header p {
      margin: 8px 0 0 0;
      color: #d1d5db;
    }
    .summary {
      padding: 20px 36px 0 36px;
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
      font-size: 18px;
    }
    .refresh-button {
      border: 0;
      border-radius: 6px;
      padding: 8px 14px;
      background: #2563eb;
      color: white;
      cursor: pointer;
    }
    .refresh-button:disabled {
      opacity: 0.6;
      cursor: wait;
    }
    .refresh-time {
      color: #6b7280;
      font-size: 14px;
    }
    .filters {
      margin: 18px 36px 0;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .filters input, .filters select, .filters button {
      min-height: 38px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      padding: 0 12px;
      background: white;
      font-size: 14px;
    }
    .filters input {
      flex: 1;
      min-width: 220px;
    }
    .filters button {
      cursor: pointer;
    }
    main {
      padding: 24px 36px 48px 36px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 24px;
    }
    .card {
      background: white;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    }
    .top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
    }
    h2 {
      margin: 0;
      font-size: 22px;
    }
    .meta {
      color: #6b7280;
      font-size: 14px;
      margin-top: 6px;
      word-break: break-all;
    }
    .badge {
      background: #6b7280;
      color: white;
      border-radius: 999px;
      padding: 6px 12px;
      font-weight: bold;
      white-space: nowrap;
    }
    .risk-high { background: #dc2626; }
    .risk-warning { background: #d97706; }
    .risk-normal { background: #16a34a; }
    .risk-unknown { background: #6b7280; }
    .image-box {
      margin: 16px 0;
      background: #0f172a;
      border-radius: 10px;
      overflow: hidden;
      text-align: center;
    }
    .image-box img {
      width: 100%;
      display: block;
    }
    .no-img {
      color: #cbd5e1;
      padding: 50px;
    }
    .section {
      background: #f9fafb;
      border-radius: 8px;
      padding: 12px;
      margin-top: 10px;
    }
    .section p {
      margin: 6px 0 0 0;
      line-height: 1.6;
      white-space: pre-wrap;
    }
    .empty {
      grid-column: 1 / -1;
      color: #6b7280;
      background: white;
      border-radius: 12px;
      padding: 32px;
      text-align: center;
    }
  </style>
</head>
<body>
  <header>
    <h1>后台事件看板 v0.4</h1>
    <p>数据来源：outputs/event_json，关键帧：outputs/keyframes</p>
  </header>

  <div class="summary">
    <span>当前显示：<b id="event-count">0</b> / 共 <b id="total-count">0</b> 条</span>
    <button id="refresh-button" class="refresh-button">刷新</button>
    <span id="refresh-time" class="refresh-time">尚未刷新</span>
  </div>

  <div class="filters">
    <input id="search-input" type="search" placeholder="搜索事件编号、视频流、摘要、原因或建议">
    <select id="risk-filter">
      <option value="">全部风险</option>
      <option value="high">高风险</option>
      <option value="warning">中风险</option>
      <option value="normal">正常</option>
      <option value="unknown">未知风险</option>
    </select>
    <select id="stream-filter">
      <option value="">全部视频流</option>
    </select>
    <select id="sort-order">
      <option value="newest">时间：最新优先</option>
      <option value="oldest">时间：最早优先</option>
    </select>
    <button id="reset-button" type="button">重置筛选</button>
  </div>

  <main id="event-list">
    <div class="empty">正在加载事件数据...</div>
  </main>

  <script>
    const eventList = document.getElementById("event-list");
    const eventCount = document.getElementById("event-count");
    const totalCount = document.getElementById("total-count");
    const refreshButton = document.getElementById("refresh-button");
    const refreshTime = document.getElementById("refresh-time");
    const searchInput = document.getElementById("search-input");
    const riskFilter = document.getElementById("risk-filter");
    const streamFilter = document.getElementById("stream-filter");
    const sortOrder = document.getElementById("sort-order");
    const resetButton = document.getElementById("reset-button");
    let allEvents = [];

    function riskInfo(level) {
      const value = text(level, "unknown").toLowerCase();
      const mapping = {
        high: ["高风险", "risk-high"],
        danger: ["高风险", "risk-high"],
        warning: ["中风险", "risk-warning"],
        medium: ["中风险", "risk-warning"],
        normal: ["正常", "risk-normal"],
        low: ["正常", "risk-normal"],
        safe: ["正常", "risk-normal"],
        unknown: ["未知风险", "risk-unknown"]
      };
      return mapping[value] || [text(level, "未知风险"), "risk-unknown"];
    }

    function text(value, fallback = "") {
      if (value === null || value === undefined || value === "") {
        return fallback;
      }
      return String(value);
    }

    function section(title, value) {
      const wrapper = document.createElement("div");
      wrapper.className = "section";

      const label = document.createElement("b");
      label.textContent = title;

      const body = document.createElement("p");
      body.textContent = text(value);

      wrapper.appendChild(label);
      wrapper.appendChild(body);
      return wrapper;
    }

    function card(event) {
      const root = document.createElement("div");
      root.className = "card";

      const top = document.createElement("div");
      top.className = "top";

      const titleBox = document.createElement("div");
      const title = document.createElement("h2");
      title.textContent = text(event.event_id, "unknown");
      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = `视频流：${text(event.stream_name, "unknown")} | 时间：${text(event.timestamp, "未知")} | JSON：${text(event.json_name)}`;
      titleBox.appendChild(title);
      titleBox.appendChild(meta);

      const badge = document.createElement("span");
      const [riskLabel, riskClass] = riskInfo(event.risk_level);
      badge.className = `badge ${riskClass}`;
      badge.textContent = riskLabel;

      top.appendChild(titleBox);
      top.appendChild(badge);

      const imageBox = document.createElement("div");
      imageBox.className = "image-box";
      if (event.keyframe_url) {
        const img = document.createElement("img");
        img.src = event.keyframe_url;
        img.alt = text(event.event_id, "keyframe");
        imageBox.appendChild(img);
      } else {
        const noImg = document.createElement("div");
        noImg.className = "no-img";
        noImg.textContent = "无关键帧";
        imageBox.appendChild(noImg);
      }

      root.appendChild(top);
      root.appendChild(imageBox);
      root.appendChild(section("触发原因：", event.trigger_reason));
      root.appendChild(section("Qwen 摘要：", event.qwen_summary));
      root.appendChild(section("风险原因：", event.risk_reason));
      root.appendChild(section("处理建议：", event.recommended_action));
      return root;
    }

    function riskGroup(level) {
      const value = text(level, "unknown").toLowerCase();
      if (["high", "danger"].includes(value)) return "high";
      if (["warning", "medium"].includes(value)) return "warning";
      if (["normal", "low", "safe"].includes(value)) return "normal";
      return "unknown";
    }

    function populateStreamFilter(events) {
      const selected = streamFilter.value;
      const streams = [...new Set(
        events.map(event => text(event.stream_name)).filter(Boolean)
      )].sort();

      streamFilter.innerHTML = '<option value="">全部视频流</option>';
      for (const stream of streams) {
        const option = document.createElement("option");
        option.value = stream;
        option.textContent = stream;
        streamFilter.appendChild(option);
      }

      if (streams.includes(selected)) {
        streamFilter.value = selected;
      }
    }

    function renderEvents() {
      const query = searchInput.value.trim().toLowerCase();
      const selectedRisk = riskFilter.value;
      const selectedStream = streamFilter.value;

      const events = allEvents.filter(event => {
        const searchable = [
          event.event_id,
          event.stream_name,
          event.qwen_summary,
          event.risk_reason,
          event.recommended_action,
          event.trigger_reason,
          event.json_name
        ].map(value => text(value).toLowerCase()).join(" ");

        return (!query || searchable.includes(query))
          && (!selectedRisk || riskGroup(event.risk_level) === selectedRisk)
          && (!selectedStream || text(event.stream_name) === selectedStream);
      });

      events.sort((a, b) => {
        const first = Number(a.json_mtime || 0);
        const second = Number(b.json_mtime || 0);
        return sortOrder.value === "oldest" ? first - second : second - first;
      });

      eventCount.textContent = String(events.length);
      totalCount.textContent = String(allEvents.length);
      eventList.innerHTML = "";

      if (!events.length) {
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = allEvents.length
          ? "没有符合筛选条件的事件"
          : "暂无事件数据";
        eventList.appendChild(empty);
        return;
      }

      for (const event of events) {
        eventList.appendChild(card(event));
      }
    }

    async function loadEvents() {
      refreshButton.disabled = true;
      try {
        const response = await fetch("/api/events", { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        allEvents = data.events || [];
        populateStreamFilter(allEvents);
        renderEvents();
        refreshTime.textContent = `最后刷新：${new Date().toLocaleString("zh-CN")}`;
      } catch (error) {
        eventList.innerHTML = "";
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = `事件数据加载失败：${error}`;
        eventList.appendChild(empty);
      } finally {
        refreshButton.disabled = false;
      }
    }

    refreshButton.addEventListener("click", loadEvents);
    searchInput.addEventListener("input", renderEvents);
    riskFilter.addEventListener("change", renderEvents);
    streamFilter.addEventListener("change", renderEvents);
    sortOrder.addEventListener("change", renderEvents);

    resetButton.addEventListener("click", () => {
      searchInput.value = "";
      riskFilter.value = "";
      streamFilter.value = "";
      sortOrder.value = "newest";
      renderEvents();
    });

    loadEvents();
    setInterval(loadEvents, 5000);
  </script>
</body>
</html>
"""
