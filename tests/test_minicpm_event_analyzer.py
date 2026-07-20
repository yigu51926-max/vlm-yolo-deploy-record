from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import minicpm_event_analyzer as analyzer  # noqa: E402


class ParseModelJsonTests(unittest.TestCase):
    def test_plain_json(self) -> None:
        result = analyzer.parse_model_json('{"summary":"道路场景","confidence":0.9}')
        self.assertEqual(result["summary"], "道路场景")

    def test_fenced_json(self) -> None:
        result = analyzer.parse_model_json('```json\n{"riskLevel":"low"}\n```')
        self.assertEqual(result["riskLevel"], "low")

    def test_json_surrounded_by_text(self) -> None:
        result = analyzer.parse_model_json('结果如下：\n{"visibleFacts":[]}\n完毕')
        self.assertEqual(result["visibleFacts"], [])

    def test_invalid_json(self) -> None:
        with self.assertRaises(analyzer.AnalyzerError):
            analyzer.parse_model_json("不是 JSON")


class EventSelectionTests(unittest.TestCase):
    EVENTS = [
        {"messageId": "old", "timestamp": "100"},
        {"messageId": "new", "timestamp": "200"},
    ]

    def test_select_by_id(self) -> None:
        result = analyzer.select_event(self.EVENTS, message_id="old", latest=False)
        self.assertEqual(result["messageId"], "old")

    def test_select_latest(self) -> None:
        result = analyzer.select_event(self.EVENTS, message_id=None, latest=True)
        self.assertEqual(result["messageId"], "new")


class ImageSelectionTests(unittest.TestCase):
    INDEX = {"eventDirectory": "20260717/example"}

    def test_annotated_has_priority(self) -> None:
        detail = {
            "images": {
                "original": {"path": "20260717/example/images/original.jpg"},
                "annotated": {"path": "20260717/example/images/annotated.jpg"},
                "detected": {"path": "20260717/example/images/detected.jpg"},
            }
        }
        self.assertEqual(
            analyzer.select_image_path(detail, self.INDEX),
            "20260717/example/images/annotated.jpg",
        )

    def test_original_is_second_choice(self) -> None:
        detail = {"data": {"images": {"original": "20260717/example/images/original.jpg"}}}
        self.assertEqual(
            analyzer.select_image_path(detail, self.INDEX),
            "20260717/example/images/original.jpg",
        )

    def test_deterministic_fallback(self) -> None:
        self.assertEqual(
            analyzer.select_image_path({}, self.INDEX),
            "20260717/example/images/annotated.jpg",
        )


class AtomicWriteTests(unittest.TestCase):
    def test_atomic_write_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analysis" / "result.json"
            analyzer.atomic_write_json(path, {"status": "ok", "中文": "正常"})
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"status": "ok", "中文": "正常"},
            )
            self.assertEqual(list(path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
