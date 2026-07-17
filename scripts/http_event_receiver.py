#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

EVENT_DIR = Path(
    os.environ.get("VA_EVENT_DIR", "/home/qi/va-test/http-events")
)
EVENT_DIR.mkdir(parents=True, exist_ok=True)


class EventHandler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok"})
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/events":
            self.send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            event = json.loads(raw.decode("utf-8"))

            message_id = str(
                event.get("messageId")
                or f"event-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
            )
            safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", message_id)

            output = EVENT_DIR / f"{safe_id}.json"
            output.write_text(
                json.dumps(event, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            summary = {
                "messageId": message_id,
                "timestamp": event.get("timestamp"),
                "channelId": event.get("videoChannelId"),
                "channelName": event.get("channelName"),
                "taskId": event.get("taskId"),
                "algorithmId": event.get("algorithmId"),
                "algorithmName": event.get("algorithmName"),
                "areaId": event.get("areaId"),
                "areaName": event.get("areaName"),
                "category": event.get("category"),
                "recordId": event.get("recordId"),
                "isRetryMessage": event.get("isRetryMessage", False),
                "property": event.get("property", {}),
                "rawFile": str(output),
            }

            with (EVENT_DIR / "events.jsonl").open(
                "a", encoding="utf-8"
            ) as file:
                file.write(json.dumps(summary, ensure_ascii=False) + "\n")

            print(
                f"[EVENT] {message_id} "
                f"{summary['channelName']} "
                f"{summary['algorithmName']}",
                flush=True,
            )
            self.send_json(200, {"resCode": 1, "resMsg": []})

        except Exception as exc:
            print(f"[ERROR] {exc}", flush=True)
            self.send_json(
                400,
                {"resCode": 0, "resMsg": [str(exc)]},
            )

    def log_message(self, fmt, *args):
        print(f"[HTTP] {self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    address = ("0.0.0.0", 18090)
    print(f"VA HTTP event receiver listening on {address}", flush=True)
    ThreadingHTTPServer(address, EventHandler).serve_forever()
