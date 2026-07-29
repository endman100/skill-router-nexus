from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_short_script.py")


class ValidateShortScriptTests(unittest.TestCase):
    def run_validator(
        self,
        text: str,
        *,
        topic: str = "Test",
        target: int | None = None,
        tolerance: float = 0.1,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        visible_count = len(re.sub(r"\s+", "", text))
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "script.md"
            source.write_text(text, encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPT),
                str(source),
                "--topic",
                topic,
                "--target",
                str(target if target is not None else visible_count),
                "--tolerance",
                str(tolerance),
                "--json",
            ]
            result = subprocess.run(command, capture_output=True, text=True)
        payload = json.loads(result.stdout) if result.stdout else {}
        return result, payload

    def test_accepts_valid_script(self) -> None:
        text = (
            "什麼是 Test？\n\n"
            "它先說明問題，再介紹技術名稱與運作方式。"
            "接著比較過往方案，補充限制，最後收束核心價值。"
        )

        result, payload = self.run_validator(text)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["errors"], [])

    def test_rejects_wrong_first_line(self) -> None:
        text = "你知道 Test 嗎？\n\n這是一段技術介紹。"

        result, payload = self.run_validator(text)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("第一個非空白行必須完全等於：什麼是 Test？", payload["errors"])

    def test_rejects_length_outside_tolerance(self) -> None:
        text = "什麼是 Test？\n\n這是一段技術介紹。"
        visible_count = len(re.sub(r"\s+", "", text))

        result, payload = self.run_validator(
            text,
            target=visible_count * 2,
            tolerance=0.0,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("字數" in error for error in payload["errors"]))

    def test_rejects_benchmark_name_dumping(self) -> None:
        text = "什麼是 Test？\n\n接著直接念出 benchmark 名稱與分數。"

        result, payload = self.run_validator(text)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("benchmark" in error for error in payload["errors"]))

    def test_rejects_call_to_action_in_ending(self) -> None:
        text = "什麼是 Test？\n\n前文說明技術。最後請立即前往官網試用。"

        result, payload = self.run_validator(text)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("行動呼籲" in error for error in payload["errors"]))

    def test_calculates_exact_ten_percent_range(self) -> None:
        text = "什麼是 Test？\n\n這是一段技術介紹。"

        _, payload = self.run_validator(text, target=720, tolerance=0.1)

        self.assertEqual(payload["allowed_range"], [648, 792])

    def test_rejects_nonstandard_vram_terms(self) -> None:
        text = "什麼是 Test？\n\n相較舊方法，它能降低顯存需求，但仍有上限。"

        result, payload = self.run_validator(text)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("VRAM" in error for error in payload["errors"]))

    def test_recognizes_traditional_method_as_comparison(self) -> None:
        text = "什麼是 Test？\n\n相對傳統做法，它降低成本，不過仍有上限。"

        _, payload = self.run_validator(text)

        self.assertFalse(any("前代" in warning for warning in payload["warnings"]))


if __name__ == "__main__":
    unittest.main()
