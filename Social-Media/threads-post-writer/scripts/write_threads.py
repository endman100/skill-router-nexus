#!/usr/bin/env python3
"""Generate a researched Threads series through Codex CLI.

The model and reasoning effort are intentionally fixed. The command refuses to
fall back when GPT-5.6 Sol is not present in the authenticated Codex catalog.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


TARGET_MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "high"
SKILL_DIR = Path(__file__).resolve().parent.parent
ROUTER_SKILL = SKILL_DIR.parent.parent / "SKILL.md"
WRITER_SKILL = SKILL_DIR / "SKILL.md"
PAPER_TOPIC_RE = re.compile(
    r"(?:"
    r"huggingface\.co/papers/|"
    r"arxiv(?:\.org|:)|"
    r"openreview\.net|"
    r"\bpaper\b|"
    r"論文|"
    r"\.pdf(?:\?|$)|"
    r"\b\d{4}\.\d{4,5}(?:v\d+)?\b|"
    r"\b10\.\d{4,9}/\S+"
    r")",
    re.IGNORECASE,
)


class WriterError(RuntimeError):
    """Base error for expected generation failures."""


class ModelUnavailableError(WriterError):
    """The authenticated Codex workspace cannot use the required model."""


class CodexInvocationError(WriterError):
    """Codex CLI failed before producing a usable draft."""


class PolicyAuditError(WriterError):
    """The generated draft violates one or more content or artifact policies."""


Runner = Callable[..., subprocess.CompletedProcess[str]]
Audit = Callable[..., dict[str, object]]


def infer_paper_mode(topic: str) -> bool:
    """Recognize explicit paper wording and common paper identifiers or URLs."""
    return bool(PAPER_TOPIC_RE.search(topic.strip()))


def unexpected_artifacts(output_path: Path, *, paper_mode: bool) -> list[Path]:
    """List top-level entries outside the declared Markdown and figure artifacts."""
    if not output_path.parent.is_dir():
        return []
    allowed_names = {output_path.name}
    if paper_mode:
        allowed_names.add(f"{output_path.stem}-figures")
    return [
        entry
        for entry in output_path.parent.iterdir()
        if entry.name not in allowed_names
    ]


def build_catalog_command(codex_path: str) -> list[str]:
    """Build a catalog request while neutralizing an invalid service-tier default."""
    return [
        codex_path,
        "debug",
        "models",
        "-c",
        'service_tier="flex"',
    ]


def build_exec_command(
    codex_path: str,
    *,
    output_path: Path,
    working_directory: Path,
) -> list[str]:
    """Build the non-interactive Codex command with immutable model settings."""
    return [
        codex_path,
        "--search",
        "--ask-for-approval",
        "never",
        "--model",
        TARGET_MODEL,
        "--config",
        f'model_reasoning_effort="{REASONING_EFFORT}"',
        "--sandbox",
        "workspace-write",
        "--cd",
        str(working_directory.resolve()),
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--color",
        "never",
        "-",
    ]


def build_prompt(
    topic: str,
    *,
    output_path: Path,
    angle: str | None = None,
    paper_mode: bool = False,
) -> str:
    """Create the task prompt consumed by the nested Codex run."""
    angle_line = angle.strip() if angle and angle.strip() else "由證據決定最有價值的單一角度"
    resolved_output = output_path.resolve()
    figure_dir = resolved_output.parent / f"{resolved_output.stem}-figures"
    validate_command = f'python "{SKILL_DIR / "validate.py"}" "{resolved_output}"'
    if paper_mode:
        paper_requirements = f"""

論文模式：開啟
論文附圖目錄：{figure_dir}

論文模式附加要求：
- 研究入口只供內部查證；發布正文不得提及 Hugging Face、arXiv、OpenReview、Semantic Scholar、Papers with Code、ResearchGate 或任何其他論文託管與發現平台
- 不要交代論文在哪裡被發現、上榜、託管或下載，直接從論文問題、方法、結果與限制開始
- 先鎖定四篇正文並完成事實與連貫性審核，之後才盤點、選取與配置圖片；不得為了遷就附圖改寫正文
- 從原始論文 PDF 或作者提供的論文資產取得所有有內容的編號 Figure；排除網頁縮圖、來源平台截圖、Logo、裝飾、公式與 Table
- 每一張論文原圖只使用一次；複合 Figure 保持為一張完整圖片，不得拆 panel 來製造額外配圖
- 將所有盤點到的論文 Figure 依 caption 與所屬章節，配置到語意最一致的 Post
- 每篇 Post 的正文下方至少放 1 張圖；同一篇可放多張，但圖片後不得再接正文
- 使用非空白的 Figure 編號與簡短 caption 作為 alt text，圖片連結只能使用相對於成品的本機路徑
- 若 Figure 少於 4 張、任一 Figure 無法與正文誠實對應、無法取得原圖或無法證明已完整盤點，停止並在聊天中說明限制，不得重複、捏造或硬塞不相關圖片
- 只可在 {figure_dir} 建立 PNG、JPEG 或 WebP 附圖；檔名使用 figure-01、figure-02 等穩定編號
"""
        completion_rule = "- 成品必須在第四篇的最後一張附圖結束，不得附加任何審稿備註或查證紀錄"
        artifact_rule = f"- 除唯一成品路徑與附圖目錄 {figure_dir} 外，不得建立或修改其他檔案，也不得執行發文"
        validate_command += " --paper"
    else:
        paper_requirements = "\n論文模式：關閉"
        completion_rule = "- 成品必須在第四篇正文結束，不得附加任何審稿備註或查證紀錄"
        artifact_rule = "- 除唯一成品路徑外，不得建立或修改其他檔案，也不得執行發文"
    return f"""你要撰寫一組經過事實核對、前後連續的繁體中文 Threads 串文

開始工作前，依序完整讀取並遵守：
1. 技能路由器：{ROUTER_SKILL}
2. 串文寫作技能：{WRITER_SKILL}

主題：{topic.strip()}
指定角度：{angle_line}
唯一成品路徑：{resolved_output}
{paper_requirements}

執行要求：
- 先上網搜尋並核對所有可能變動的事實
- 優先採用官方公告、官方文件、系統卡、原始論文與其他第一手來源
- OpenAI 產品只採用 OpenAI 官方來源，除非主題本身需要外部比較
- 依 threads-post-writer 的 prose-first 流程完成連續串文
- 執行 threads-post-writer 的 Hook Gate；主題有明確核心名稱時，首個非空白正文行採「核心名稱：具體定位＋核心創新」，不要先鋪陳領域背景
- 執行 threads-post-writer 的 Conclusion Gate；第四篇最後 1–2 個正文行必須回收第一篇承諾並給出有邊界的明確判斷，最後一行本身必須包含核心名稱或只有該主題才成立的機制，限制不能取代結論，不得只以「值得關注／提供一條路線／未來可期」等泛用前景句收尾
- 來源只供內部查證；成品不得包含來源清單、核對來源、URL 或引用
{completion_rule}
- 將最終 Markdown 直接寫入唯一成品路徑，不要把文章正文當成最終聊天回答
{artifact_rule}
- 寫檔後執行：{validate_command}
- 若文字審核失敗，修改同一成品檔並重跑，直到審核通過
- 最終聊天回答只回報成品路徑與審核結果
"""


def _run(
    runner: Runner,
    command: list[str],
    *,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return runner(
        command,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def require_model_access(codex_path: str, *, runner: Runner = subprocess.run) -> None:
    """Require the target model and requested effort in the current Codex catalog."""
    completed = _run(runner, build_catalog_command(codex_path))
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise CodexInvocationError(f"無法讀取 Codex 模型目錄：{detail}")

    try:
        payload: dict[str, Any] = json.loads(completed.stdout)
        models = payload["models"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise CodexInvocationError("Codex 模型目錄不是可辨識的 JSON") from error

    target = next(
        (model for model in models if model.get("slug") == TARGET_MODEL),
        None,
    )
    if target is None:
        raise ModelUnavailableError(
            f"目前登入的 Codex workspace 沒有 {TARGET_MODEL} 權限；"
            "已停止，未改用其他模型"
        )

    efforts = {
        item.get("effort")
        for item in target.get("supported_reasoning_levels", [])
        if isinstance(item, dict)
    }
    if REASONING_EFFORT not in efforts:
        raise ModelUnavailableError(
            f"{TARGET_MODEL} 的模型目錄未列出 reasoning={REASONING_EFFORT}；"
            "已停止，未降低 reasoning"
        )


def _load_default_audit() -> Audit:
    validator_path = SKILL_DIR / "validate.py"
    spec = importlib.util.spec_from_file_location("threads_post_validator", validator_path)
    if spec is None or spec.loader is None:
        raise CodexInvocationError(f"無法載入文字審核器：{validator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_file


def generate_article(
    topic: str,
    *,
    output_path: Path,
    angle: str | None = None,
    paper_mode: bool = False,
    codex_path: str,
    working_directory: Path,
    runner: Runner = subprocess.run,
    audit: Audit | None = None,
) -> Path:
    """Generate, save, and audit one Threads series."""
    if not topic.strip():
        raise WriterError("主題不可為空")
    effective_paper_mode = paper_mode or infer_paper_mode(topic)

    working_directory = working_directory.expanduser().resolve()
    if not working_directory.is_dir():
        raise WriterError(f"工作目錄不存在：{working_directory}")

    output_path = output_path.expanduser().resolve()
    try:
        output_path.relative_to(working_directory)
    except ValueError as error:
        raise WriterError(
            f"輸出路徑必須位於 Codex 工作目錄內：{working_directory}"
        ) from error
    if output_path.parent == working_directory:
        raise WriterError(
            "輸出必須放在工作目錄內的專用子目錄，避免 nested Codex "
            "取得整個專案根目錄的寫入範圍"
        )
    preexisting_unexpected = unexpected_artifacts(
        output_path,
        paper_mode=effective_paper_mode,
    )
    if preexisting_unexpected:
        names = "、".join(path.name for path in preexisting_unexpected)
        raise WriterError(f"輸出子目錄不是專用目錄，含有非成品項目：{names}")

    require_model_access(codex_path, runner=runner)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_exec_command(
        codex_path,
        output_path=output_path,
        working_directory=output_path.parent,
    )

    completed = _run(
        runner,
        command,
        input_text=build_prompt(
            topic,
            angle=angle,
            output_path=output_path,
            paper_mode=effective_paper_mode,
        ),
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise CodexInvocationError(f"Codex 寫作失敗：{detail}")
    if not output_path.is_file() or not output_path.read_text(
        encoding="utf-8"
    ).strip():
        raise CodexInvocationError(
            "Codex 沒有直接建立指定的 Markdown；未使用聊天文字作為替代"
        )

    generated_unexpected = unexpected_artifacts(
        output_path,
        paper_mode=effective_paper_mode,
    )
    if generated_unexpected:
        names = "、".join(path.name for path in generated_unexpected)
        raise PolicyAuditError(f"nested Codex 建立了未授權的額外項目：{names}")

    if audit is None:
        audit_result = _load_default_audit()(
            output_path,
            paper_mode=effective_paper_mode,
        )
    else:
        audit_result = audit(output_path)
    if not audit_result.get("ok"):
        details = [
            *[str(term) for term in audit_result.get("blacklist_hits", [])],
            *[str(term) for term in audit_result.get("paper_source_hits", [])],
            *[str(term) for term in audit_result.get("paper_errors", [])],
        ]
        raise PolicyAuditError(f"文章已保存，但內容審核失敗：{'、'.join(details)}")

    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "用 Codex CLI 與固定的 gpt-5.6-sol / reasoning=high "
            "撰寫並核對 Threads 串文"
        )
    )
    parser.add_argument("topic", help="簡短主題，例如 GPT-5.6")
    parser.add_argument("--angle", help="可選的單一文章角度")
    parser.add_argument(
        "--paper",
        action="store_true",
        help="明確啟用論文模式；常見論文 URL、識別碼與『論文／paper』字樣也會自動啟用",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("threads-output/threads-draft.md"),
        help="Markdown 輸出路徑（預設：threads-output/threads-draft.md）",
    )
    parser.add_argument(
        "--working-directory",
        "-C",
        type=Path,
        default=Path.cwd(),
        help="Codex 工作目錄（預設：目前目錄）",
    )
    parser.add_argument(
        "--codex-path",
        help="Codex 執行檔路徑；通常不需要指定",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    codex_path = args.codex_path or shutil.which("codex")
    if not codex_path:
        print("[錯誤] 找不到 codex CLI，請先安裝並登入", file=sys.stderr)
        return 2

    print(
        f"使用固定模型 {TARGET_MODEL}，reasoning={REASONING_EFFORT}",
        file=sys.stderr,
    )
    try:
        output = generate_article(
            args.topic,
            angle=args.angle,
            paper_mode=args.paper,
            output_path=args.output,
            codex_path=codex_path,
            working_directory=args.working_directory,
        )
    except ModelUnavailableError as error:
        print(f"[模型不可用] {error}", file=sys.stderr)
        return 3
    except PolicyAuditError as error:
        print(f"[審核失敗] {error}", file=sys.stderr)
        return 5
    except WriterError as error:
        print(f"[錯誤] {error}", file=sys.stderr)
        return 4

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
