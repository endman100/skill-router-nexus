from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "SKILL.md"


def router_body() -> str:
    content = ROUTER.read_text(encoding="utf-8")
    return content[content.index("## 路由流程") :]


def test_lifecycle_has_five_ordered_stages() -> None:
    body = router_body()
    markers = [
        "| `UNDERSTAND` |",
        "| `PLAN` |",
        "| `EXECUTE` |",
        "| `VERIFY` |",
        "| `DELIVER` |",
    ]
    positions = [body.index(marker) for marker in markers]

    assert positions == sorted(positions)
    assert body.count("### Step ") == 5
    assert "`PLAN` | 條件式" in body


def test_per_stage_limits_replace_global_quotas() -> None:
    body = router_body()

    assert "每階段搜尋 1 到 2 個分類" in body
    assert "每階段保留 1 到 4 個合格候選" in body
    assert "每階段通常載入 1 個、最多 2 個 skill" in body
    assert "總數建議 2 到 6 個 skill" not in body
    assert "先判斷任務主軸，再圈出 2 到 4 個候選分類" not in body


def test_search_expands_sequentially_and_reuses_scans() -> None:
    body = router_body()

    assert '--category Video-Generation\n' in body
    assert '--category Creative-Video-Generation\n' in body
    assert '--category Video-Generation --category Creative-Video-Generation' not in body
    assert body.count('python -B "<SKILL_DIR>/skill_reader.py"') == 2
    assert "已掃描過的分類結果" in body


def test_unresolved_path_can_report_partial_or_blocked() -> None:
    body = router_body()

    assert "`PARTIAL`" in body
    assert "`BLOCKED`" in body
    assert "不得宣告 `COMPLETED`" in body
    assert "最小阻塞報告" in body


def test_verification_evidence_is_operational() -> None:
    body = router_body()

    for marker in (
        "檢查命令或資料來源",
        "執行時間或 revision",
        "exit code／斷言結果",
        "失敗數",
        "晚於最後一次修改",
    ):
        assert marker in body


def test_delivery_routes_to_dedicated_category() -> None:
    content = ROUTER.read_text(encoding="utf-8")
    body = router_body()

    assert "`Agent-Delivery/`" in content
    assert "`DELIVER`：先選 `Agent-Delivery`" in body
    assert "`<COMPLETED|PARTIAL|BLOCKED>`" in body


def test_duplicate_policy_defines_path_and_content_identity() -> None:
    body = router_body()

    assert "resolved absolute path" in body
    assert "SHA-256" in body
    assert "字典序最小" in body
    assert "hash-only" in body


def test_missing_description_has_targeted_fallback() -> None:
    body = router_body()

    assert "description 缺失" in body
    assert "標題與開頭用途段落" in body
    assert "metadata debt" in body


def test_composite_workflows_use_declared_progressive_dependencies() -> None:
    body = router_body()

    assert "複合 workflow 的 dependency 載入" in body
    assert "明確相對路徑及載入條件" in body
    assert "一次全部預載" in body
    assert "reference dependency 屬 progressive disclosure" in body
    assert "不得取代 Router 的通用 VERIFY 與 DELIVER" in body


def test_bounded_revision_loop_returns_to_verification() -> None:
    body = router_body()

    assert "有界修訂循環" in body
    assert "EXECUTE(revision) → VERIFY" in body
    assert "最大輪數" in body
    assert "每輪修改後都要取得較新的驗證證據" in body
