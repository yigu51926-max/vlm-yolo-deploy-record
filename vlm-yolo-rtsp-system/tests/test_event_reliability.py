import json
import os
import re
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend import dashboard_server, generate_dashboard
from scripts import (
    qwen_analyze_image,
    yolo_qwen_event_demo,
    yolo_qwen_event_json_demo,
)
from scripts.event_utils import (
    atomic_write_json,
    generate_event_id,
    normalize_risk_level,
)


class EventReliabilityTests(unittest.TestCase):
    def test_event_ids_are_unique(self):
        event_ids = [generate_event_id() for _ in range(1000)]

        self.assertEqual(len(event_ids), len(set(event_ids)))
        for event_id in event_ids:
            self.assertRegex(
                event_id,
                re.compile(r"^event_\d{8}T\d{12}Z_[0-9a-f]{8}$"),
            )

    def test_event_ids_are_unique_under_concurrency(self):
        with ThreadPoolExecutor(max_workers=16) as executor:
            event_ids = list(executor.map(lambda _: generate_event_id(), range(2000)))

        self.assertEqual(len(event_ids), len(set(event_ids)))

    def test_atomic_write_json_has_no_temp_file_left(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            target = directory / "event_test.json"
            payload = {"event_id": "event_test", "risk_level": "normal"}

            result = atomic_write_json(target, payload)

            self.assertEqual(result, target)
            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")),
                payload,
            )
            self.assertEqual(list(directory.glob("*.tmp")), [])
            self.assertEqual(list(directory.glob(".*.tmp")), [])

    def test_atomic_write_json_cleans_temp_file_on_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            target = directory / "event_error.json"

            with self.assertRaises(TypeError):
                atomic_write_json(target, {"invalid": object()})

            self.assertFalse(target.exists())
            self.assertEqual(list(directory.glob("*.tmp")), [])
            self.assertEqual(list(directory.glob(".*.tmp")), [])

    def test_atomic_write_failure_preserves_existing_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            target = directory / "event_existing.json"
            original = {"event_id": "event_existing", "risk_level": "normal"}
            atomic_write_json(target, original)
            replace_paths = []

            def fail_replace(source, destination):
                replace_paths.append((Path(source), Path(destination)))
                raise OSError("simulated replace failure")

            with patch("scripts.event_utils.os.replace", side_effect=fail_replace):
                with self.assertRaises(OSError):
                    atomic_write_json(
                        target,
                        {"event_id": "event_replacement", "risk_level": "high"},
                    )

            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")),
                original,
            )
            self.assertEqual(len(replace_paths), 1)
            source, destination = replace_paths[0]
            self.assertEqual(source.parent, target.parent)
            self.assertEqual(destination, target)
            self.assertEqual(list(directory.glob("*.tmp")), [])
            self.assertEqual(list(directory.glob(".*.tmp")), [])

    def test_risk_level_mapping(self):
        expected = {
            "high": "high",
            "warning": "warning",
            "normal": "normal",
            "unknown": "unknown",
            "low": "normal",
            "danger": "high",
            "medium": "warning",
            "safe": "normal",
            "": "unknown",
            None: "unknown",
            "invalid": "unknown",
        }

        for raw_level, normalized in expected.items():
            with self.subTest(raw_level=raw_level):
                self.assertEqual(normalize_risk_level(raw_level), normalized)

    def test_event_id_is_shared_by_all_event_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            event_id = generate_event_id()
            config = {"outputs": {"event_log_dir": str(directory)}}
            expected_keyframe = directory / f"{event_id}_cam1.jpg"
            expected_log = directory / f"qwen_analysis_{event_id}.txt"
            expected_json = directory / f"{event_id}.json"
            result = SimpleNamespace(plot=lambda: object())

            self.assertEqual(
                qwen_analyze_image.make_log_path(
                    config,
                    directory / "frame.jpg",
                    event_id,
                ),
                expected_log,
            )

            with patch(
                "scripts.yolo_qwen_event_json_demo.cv2.imwrite",
                return_value=True,
            ):
                keyframe = yolo_qwen_event_json_demo.save_keyframe(
                    object(),
                    result,
                    directory,
                    "cam1",
                    event_id,
                )
            self.assertEqual(Path(keyframe), expected_keyframe)

            with patch(
                "scripts.yolo_qwen_event_json_demo.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as run:
                returncode, log_path = yolo_qwen_event_json_demo.call_qwen(
                    "configs/collaboration_config.json",
                    str(expected_keyframe),
                    "person 0.99",
                    event_id,
                    directory,
                )
            self.assertEqual(returncode, 0)
            self.assertEqual(Path(log_path), expected_log)
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--event-id") + 1], event_id)

            json_path = yolo_qwen_event_json_demo.save_event_json(
                directory,
                {"event_id": event_id, "risk_level": "normal"},
            )
            self.assertEqual(Path(json_path), expected_json)

            with patch(
                "scripts.yolo_qwen_event_demo.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as run:
                yolo_qwen_event_demo.call_qwen(
                    "configs/collaboration_config.json",
                    str(expected_keyframe),
                    "person 0.99",
                    event_id,
                )
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--event-id") + 1], event_id)

    def test_dashboard_keeps_valid_events_when_json_is_corrupt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            event_dir = Path(temp_dir)
            atomic_write_json(
                event_dir / "event_normal.json",
                {
                    "event_id": "event_normal",
                    "risk_level": "normal",
                    "keyframe_path": "/tmp/event_normal.jpg",
                },
            )
            atomic_write_json(
                event_dir / "event_low.json",
                {
                    "event_id": "event_low",
                    "risk_level": "low",
                    "keyframe_path": "/tmp/event_low.jpg",
                },
            )
            (event_dir / "event_broken.json").write_text(
                '{"event_id": ',
                encoding="utf-8",
            )
            (event_dir / ".event_pending.json.tmp").write_text(
                '{"event_id": "temporary"}',
                encoding="utf-8",
            )
            (event_dir / "notes.txt").write_text("ignored", encoding="utf-8")
            os.utime(event_dir / "event_normal.json", (100, 100))
            os.utime(event_dir / "event_low.json", (200, 200))

            with patch.object(dashboard_server, "EVENT_DIR", event_dir):
                with self.assertLogs(
                    dashboard_server.LOGGER,
                    level="WARNING",
                ) as captured:
                    events = dashboard_server.load_events()

            self.assertEqual(
                [event["event_id"] for event in events],
                ["event_low", "event_normal"],
            )
            levels = {event["event_id"]: event["risk_level"] for event in events}
            self.assertEqual(levels["event_normal"], "normal")
            self.assertEqual(levels["event_low"], "normal")

            with patch.object(generate_dashboard, "EVENT_DIR", event_dir):
                with self.assertLogs(
                    generate_dashboard.LOGGER,
                    level="WARNING",
                ):
                    static_events = generate_dashboard.load_events()

            static_levels = {
                event["event_id"]: event["risk_level"]
                for event in static_events
            }
            self.assertEqual(static_levels, levels)
            warning_text = "\n".join(captured.output)
            self.assertIn("event_broken.json", warning_text)
            self.assertNotIn("Traceback", warning_text)
            self.assertNotIn("{\"event_id\"", warning_text)


if __name__ == "__main__":
    unittest.main()
