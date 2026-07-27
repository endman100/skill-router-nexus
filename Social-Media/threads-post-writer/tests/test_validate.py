from __future__ import annotations

import hashlib
import importlib.util
import inspect
import struct
import tempfile
import unittest
import zlib
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "threads_post_validator",
    SKILL_DIR / "validate.py",
)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def make_png(red: int, green: int, blue: int) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    signature = b"\x89PNG\r\n\x1a\n"
    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixels = zlib.compress(b"\x00" + bytes((red, green, blue)))
    return signature + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")


class PaperModeAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.figure_dir = self.root / "draft-figures"
        self.figure_dir.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_figure(self, name: str, payload: bytes) -> str:
        target = self.figure_dir / name
        target.write_bytes(payload)
        return f"draft-figures/{name}"

    def _write_draft(self, posts: list[tuple[str, list[str]]]) -> Path:
        blocks: list[str] = []
        figure_number = 1
        for prose, figures in posts:
            lines = [prose, ""]
            for figure in figures:
                lines.append(
                    f"![Figure {figure_number}：論文原圖]({figure})"
                )
                figure_number += 1
            blocks.append("\n".join(lines))
        draft = self.root / "draft.md"
        draft.write_text("\n\n---\n\n".join(blocks), encoding="utf-8")
        return draft

    def _audit_paper(self, draft: Path) -> dict[str, object]:
        parameters = inspect.signature(VALIDATOR.audit_file).parameters
        if "paper_mode" in parameters:
            return VALIDATOR.audit_file(draft, paper_mode=True)
        return VALIDATOR.audit_file(draft)

    def _valid_posts(self) -> list[tuple[str, list[str]]]:
        paths = [
            self._write_figure(
                f"figure-{index:02d}.png",
                make_png(index * 30, index * 20, index * 10),
            )
            for index in range(1, 5)
        ]
        return [
            ("這項方法先處理輸入表示的限制", [paths[0]]),
            ("接著把計算瓶頸移到較小的狀態空間", [paths[1]]),
            ("核心機制透過分層路由保留重要訊號", [paths[2]]),
            ("實驗結果顯示效能與成本存在明確取捨", [paths[3]]),
        ]

    def test_accepts_unique_local_paper_figures_below_every_post(self) -> None:
        result = self._audit_paper(self._write_draft(self._valid_posts()))

        self.assertTrue(result["ok"])
        self.assertEqual(result.get("paper_image_count"), 4)
        self.assertEqual(result.get("paper_errors"), [])

    def test_rejects_paper_hosting_platform_in_publishable_copy(self) -> None:
        posts = self._valid_posts()
        posts[0] = ("這篇論文在 Hugging Face 上受到關注", posts[0][1])

        result = self._audit_paper(self._write_draft(posts))

        self.assertFalse(result["ok"])
        self.assertIn("Hugging Face", result.get("paper_source_hits", []))

    def test_rejects_post_without_a_figure(self) -> None:
        posts = self._valid_posts()
        posts[2] = (posts[2][0], [])

        result = self._audit_paper(self._write_draft(posts))

        self.assertFalse(result["ok"])
        self.assertTrue(
            any("第 3 篇" in error for error in result.get("paper_errors", []))
        )

    def test_rejects_duplicate_content_even_when_paths_differ(self) -> None:
        posts = self._valid_posts()
        duplicate_payload = (self.figure_dir / "figure-01.png").read_bytes()
        duplicate = self._write_figure("figure-99.png", duplicate_payload)
        posts[3] = (posts[3][0], [duplicate])

        result = self._audit_paper(self._write_draft(posts))

        self.assertFalse(result["ok"])
        digest = hashlib.sha256(duplicate_payload).hexdigest()
        self.assertIn(digest, result.get("duplicate_image_hashes", []))

    def test_rejects_prose_after_a_figure(self) -> None:
        draft = self._write_draft(self._valid_posts())
        text = draft.read_text(encoding="utf-8")
        text = text.replace(
            "![Figure 1：論文原圖](draft-figures/figure-01.png)",
            "![Figure 1：論文原圖](draft-figures/figure-01.png)\n這行不應出現在圖片後",
            1,
        )
        draft.write_text(text, encoding="utf-8")

        result = self._audit_paper(draft)

        self.assertFalse(result["ok"])
        self.assertTrue(
            any("圖片之後" in error for error in result.get("paper_errors", []))
        )

    def test_rejects_remote_figure_url(self) -> None:
        posts = self._valid_posts()
        posts[1] = (posts[1][0], ["https://example.com/figure-2.png"])

        result = self._audit_paper(self._write_draft(posts))

        self.assertFalse(result["ok"])
        self.assertTrue(
            any("本機相對路徑" in error for error in result.get("paper_errors", []))
        )

    def test_rejects_non_image_outside_expected_figure_directory(self) -> None:
        posts = self._valid_posts()
        misc = self.root / "misc"
        misc.mkdir()
        fake = misc / "figure-77.txt"
        fake.write_text("not an image", encoding="utf-8")
        posts[3] = (posts[3][0], ["misc/figure-77.txt"])

        result = self._audit_paper(self._write_draft(posts))

        self.assertFalse(result["ok"])
        self.assertTrue(
            any("指定附圖目錄" in error for error in result.get("paper_errors", []))
        )

    def test_rejects_alt_text_without_figure_number_and_caption(self) -> None:
        draft = self._write_draft(self._valid_posts())
        text = draft.read_text(encoding="utf-8").replace(
            "![Figure 1：論文原圖]",
            "![任意替代文字]",
            1,
        )
        draft.write_text(text, encoding="utf-8")

        result = self._audit_paper(draft)

        self.assertFalse(result["ok"])
        self.assertTrue(
            any("Figure 編號與 caption" in error for error in result.get("paper_errors", []))
        )

    def test_rejects_additional_paper_platform_and_visible_url(self) -> None:
        posts = self._valid_posts()
        posts[0] = (
            "這份內容收錄在 bioRxiv，詳見 https://example.com/paper",
            posts[0][1],
        )

        result = self._audit_paper(self._write_draft(posts))

        self.assertFalse(result["ok"])
        self.assertIn("bioRxiv", result.get("paper_source_hits", []))
        self.assertTrue(result.get("url_hits"))

    def test_rejects_zenodo_doi_citation_and_schemeless_link(self) -> None:
        posts = self._valid_posts()
        posts[0] = (
            "資料收錄於 Zenodo，識別碼是 10.5281/zenodo.123，另見 [1] 與 [來源](example.com/paper)",
            posts[0][1],
        )

        result = self._audit_paper(self._write_draft(posts))

        self.assertFalse(result["ok"])
        self.assertIn("Zenodo", result.get("paper_source_hits", []))
        self.assertTrue(result.get("citation_hits"))

    def test_rejects_unreferenced_file_in_figure_directory(self) -> None:
        draft = self._write_draft(self._valid_posts())
        self._write_figure("figure-05.png", make_png(201, 202, 203))

        result = self._audit_paper(draft)

        self.assertFalse(result["ok"])
        self.assertTrue(
            any("未在文章中使用" in error for error in result.get("paper_errors", []))
        )

    def test_base_mode_rejects_non_four_post_draft_and_visible_url(self) -> None:
        draft = self.root / "ordinary.md"
        draft.write_text("單篇內容 https://example.com", encoding="utf-8")

        result = VALIDATOR.audit_file(draft)

        self.assertFalse(result["ok"])
        self.assertTrue(result.get("structure_errors"))
        self.assertTrue(result.get("url_hits"))

    def test_rejects_json_that_mimics_four_markdown_posts(self) -> None:
        source = self.root / "legacy.json"
        source.write_text(
            '[["一"], ["---"], ["二"], ["---"], ["三"], ["---"], ["四"]]',
            encoding="utf-8",
        )

        result = VALIDATOR.audit_file(source)

        self.assertFalse(result["ok"])
        self.assertTrue(result.get("format_errors"))


if __name__ == "__main__":
    unittest.main()
