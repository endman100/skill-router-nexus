from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "threads_post_writer",
    SKILL_DIR / "scripts" / "write_threads.py",
)
assert SPEC is not None and SPEC.loader is not None
WRITER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WRITER)


class PaperModePromptTests(unittest.TestCase):
    def test_build_prompt_exposes_paper_mode(self) -> None:
        self.assertIn("paper_mode", inspect.signature(WRITER.build_prompt).parameters)

    def test_prompt_requires_named_positioning_hook_before_background(self) -> None:
        prompt = WRITER.build_prompt(
            "一個有明確方法名的 AI 主題",
            output_path=Path("named-method.md"),
        )

        self.assertIn("Hook Gate", prompt)
        self.assertIn("核心名稱：具體定位＋核心創新", prompt)
        self.assertIn("首個非空白正文行", prompt)
        self.assertIn("不要先鋪陳領域背景", prompt)

    def test_skill_persists_the_approved_named_positioning_strategy(self) -> None:
        skill_text = WRITER.WRITER_SKILL.read_text(encoding="utf-8")

        self.assertIn("核心名稱：具體定位＋核心創新", skill_text)
        self.assertIn("Hook Gate", skill_text)
        self.assertIn(
            "SpectraReward：讓 LLM「讀回 Prompt」的全新圖片評估方法",
            skill_text,
        )

    def test_prompt_requires_conclusion_gate_for_final_prose_lines(self) -> None:
        prompt = WRITER.build_prompt(
            "一個需要明確收尾的 AI 主題",
            output_path=Path("bounded-conclusion.md"),
        )

        self.assertIn("Conclusion Gate", prompt)
        self.assertIn("第四篇最後 1–2 個正文行", prompt)
        self.assertIn("回收第一篇承諾", prompt)
        self.assertIn("有邊界的明確判斷", prompt)
        self.assertIn("最後一行本身必須包含核心名稱或只有該主題才成立的機制", prompt)
        self.assertIn("不得只以「值得關注／提供一條路線／未來可期」", prompt)

    def test_skill_persists_the_bounded_thesis_payoff_strategy(self) -> None:
        skill_text = WRITER.WRITER_SKILL.read_text(encoding="utf-8")

        self.assertIn("Conclusion Gate", skill_text)
        self.assertIn("先讀第一篇前兩個正文行，再讀第四篇最後兩個正文行", skill_text)
        self.assertIn("移除核心名稱，或換成另一個方法", skill_text)
        self.assertIn("限制不能取代結論", skill_text)
        self.assertIn("不會取代", skill_text)
        self.assertIn("提供一條路線", skill_text)

    def test_skill_requires_a_subject_specific_final_line(self) -> None:
        skill_text = WRITER.WRITER_SKILL.read_text(encoding="utf-8")

        self.assertIn("最後一個正文行本身", skill_text)
        self.assertIn("核心名稱或只有這個主題才成立的機制", skill_text)
        self.assertIn("不能只靠前一行命名，再用代名詞收在泛用判斷", skill_text)

    def test_paper_prompt_locks_prose_before_mapping_all_figures(self) -> None:
        parameters = inspect.signature(WRITER.build_prompt).parameters
        kwargs: dict[str, object] = {
            "output_path": Path("paper-thread.md"),
        }
        if "paper_mode" in parameters:
            kwargs["paper_mode"] = True

        prompt = WRITER.build_prompt("一篇新的視覺模型論文", **kwargs)

        self.assertIn("不得提及 Hugging Face、arXiv", prompt)
        self.assertIn("先鎖定四篇正文", prompt)
        self.assertIn("每一張論文原圖只使用一次", prompt)
        self.assertIn("每篇 Post 的正文下方", prompt)
        self.assertIn("--paper", prompt)

    def test_cli_documents_explicit_paper_mode(self) -> None:
        help_text = WRITER.build_parser().format_help()

        self.assertIn("--paper", help_text)

    def test_paper_validator_command_quotes_paths_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="paper thread ") as temp_dir:
            output = Path(temp_dir) / "draft with spaces.md"
            prompt = WRITER.build_prompt(
                "論文主題",
                output_path=output,
                paper_mode=True,
            )

        expected = (
            f'python "{WRITER.SKILL_DIR / "validate.py"}" '
            f'"{output.resolve()}" --paper'
        )
        self.assertIn(expected, prompt)

    def test_obvious_paper_topics_are_detected(self) -> None:
        self.assertTrue(hasattr(WRITER, "infer_paper_mode"))
        self.assertTrue(WRITER.infer_paper_mode("幫我讀這篇論文"))
        self.assertTrue(
            WRITER.infer_paper_mode("https://huggingface.co/papers/2607.11886")
        )
        self.assertTrue(WRITER.infer_paper_mode("arXiv:2607.11886"))
        self.assertTrue(WRITER.infer_paper_mode("2607.11886"))
        self.assertFalse(WRITER.infer_paper_mode("GPT-5.6 產品更新"))

    def test_generation_auto_enables_paper_mode_and_scopes_nested_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "dedicated" / "paper.md"
            exec_command: list[str] = []
            prompt_text = ""

            def runner(
                command: list[str],
                **kwargs: object,
            ) -> subprocess.CompletedProcess[str]:
                nonlocal exec_command, prompt_text
                if "models" in command:
                    catalog = {
                        "models": [
                            {
                                "slug": WRITER.TARGET_MODEL,
                                "supported_reasoning_levels": [
                                    {"effort": WRITER.REASONING_EFFORT}
                                ],
                            }
                        ]
                    }
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        stdout=json.dumps(catalog),
                        stderr="",
                    )
                exec_command = command
                prompt_text = str(kwargs.get("input", ""))
                output.write_text("一\n\n---\n\n二\n\n---\n\n三\n\n---\n\n四", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            WRITER.generate_article(
                "https://huggingface.co/papers/2607.11886",
                output_path=output,
                codex_path="codex",
                working_directory=root,
                runner=runner,
                audit=lambda _: {"ok": True},
            )

        self.assertIn("論文模式：開啟", prompt_text)
        cd_index = exec_command.index("--cd")
        self.assertEqual(exec_command[cd_index + 1], str(output.parent.resolve()))

    def test_nonpaper_generation_preserves_unary_custom_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "threads-output" / "draft.md"

            def runner(
                command: list[str],
                **_: object,
            ) -> subprocess.CompletedProcess[str]:
                if "models" in command:
                    catalog = {
                        "models": [
                            {
                                "slug": WRITER.TARGET_MODEL,
                                "supported_reasoning_levels": [
                                    {"effort": WRITER.REASONING_EFFORT}
                                ],
                            }
                        ]
                    }
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        stdout=json.dumps(catalog),
                        stderr="",
                    )
                output.write_text("第一篇\n\n---\n\n第二篇\n\n---\n\n第三篇\n\n---\n\n第四篇", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            def unary_audit(_: Path) -> dict[str, object]:
                return {"ok": True, "blacklist_hits": []}

            try:
                result = WRITER.generate_article(
                    "一般技術主題",
                    output_path=output,
                    codex_path="codex",
                    working_directory=root,
                    runner=runner,
                    audit=unary_audit,
                )
            except TypeError as error:
                self.fail(f"一參數自訂 audit 不應因新增論文模式而失效：{error}")

            self.assertEqual(result, output.resolve())

    def test_generation_rejects_output_directly_in_working_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            def unexpected_runner(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
                self.fail("輸出目錄檢查應在模型或 nested Codex 啟動前完成")

            with self.assertRaises(WRITER.WriterError):
                WRITER.generate_article(
                    "一般技術主題",
                    output_path=root / "draft.md",
                    codex_path="codex",
                    working_directory=root,
                    runner=unexpected_runner,
                    audit=lambda _: {"ok": True},
                )

    def test_generation_rejects_output_directory_with_unrelated_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "threads-output"
            output_dir.mkdir()
            (output_dir / "keep.txt").write_text("user file", encoding="utf-8")

            def unexpected_runner(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
                self.fail("非專用目錄應在模型或 nested Codex 啟動前被拒絕")

            with self.assertRaises(WRITER.WriterError):
                WRITER.generate_article(
                    "一般技術主題",
                    output_path=output_dir / "draft.md",
                    codex_path="codex",
                    working_directory=root,
                    runner=unexpected_runner,
                    audit=lambda _: {"ok": True},
                )

    def test_generation_rejects_unexpected_nested_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "threads-output" / "draft.md"

            def runner(
                command: list[str],
                **_: object,
            ) -> subprocess.CompletedProcess[str]:
                if "models" in command:
                    catalog = {
                        "models": [
                            {
                                "slug": WRITER.TARGET_MODEL,
                                "supported_reasoning_levels": [
                                    {"effort": WRITER.REASONING_EFFORT}
                                ],
                            }
                        ]
                    }
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        stdout=json.dumps(catalog),
                        stderr="",
                    )
                output.write_text("一\n\n---\n\n二\n\n---\n\n三\n\n---\n\n四", encoding="utf-8")
                (output.parent / "unexpected.txt").write_text(
                    "unexpected",
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with self.assertRaises(WRITER.PolicyAuditError):
                WRITER.generate_article(
                    "一般技術主題",
                    output_path=output,
                    codex_path="codex",
                    working_directory=root,
                    runner=runner,
                    audit=lambda _: {"ok": True},
                )


if __name__ == "__main__":
    unittest.main()
