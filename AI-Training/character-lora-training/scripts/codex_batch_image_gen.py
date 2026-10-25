#!/usr/bin/env python3
"""Design every dataset case, then generate one isolated image per case.

Codex writes <folder>/cases.json (keep N + change 2N) before any image.
Re-runs reuse that plan and create only missing files (01.png, 02.png, ...).

  codex_batch_image_gen.py N <reference> <folder>
  codex_batch_image_gen.py N <reference> <folder> --design-only
  codex_batch_image_gen.py N <reference> <folder> --dry-run
  codex_batch_image_gen.py N <reference> <folder> --only change_02

Top up change_outfit from the same plan (never keep, and never overwrite a valid PNG):

  codex_batch_image_gen.py --fill-existing <change_outfit> --target 2N --reference <reference> N
"""

import argparse
from ws import parse_args
import base64
import binascii
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib


DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_COUNT = 30
DEFAULT_MAX_ROUNDS = 3
DEFAULT_EFFORT = "medium"
DEFAULT_TIMEOUT = 900
DEFAULT_PLAN_TIMEOUT = 1800
# Kept in the same order as reference_codex_judge.py. Image generation is the
# sole exception at command construction time; tests compare the entire tuple.
DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "code_mode_host", "shell_snapshot", "apps",
    "plugins", "remote_plugin", "plugin_sharing", "browser_use",
    "browser_use_external", "browser_use_full_cdp_access", "computer_use",
    "in_app_browser", "hooks", "image_generation", "multi_agent",
    "workspace_dependencies", "skill_mcp_dependency_install",
    "tool_call_mcp_elicitation", "tool_suggest", "goals", "guardian_approval",
    "auth_elicitation", "personality",
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
KEEP = "keep_outfit"
CHANGE = "change_outfit"
ALL_GROUPS = (KEEP, CHANGE)
ASPECT_RATIOS = ("1:1", "4:3", "3:4", "16:9", "9:16")
TEXT_FIELDS = ("background", "pose", "action", "expression", "camera")
KEEP_OUTFIT = "identical to the reference front view"
STYLE_TEXT = (
    "採用乾淨的日系動畫賽璐璐上色，線稿俐落，色塊均勻，陰影簡潔，漸層平滑。"
    "皮膚與服裝表面乾淨，不添加膠片顆粒、紙張紋理、斑駁筆觸、細碎雜點或過度銳化。"
    "背景使用簡潔的動畫美術風格，避免密集零碎的材質細節。保留角色與服裝的必要細節。"
)
GROK_KEEP_PROMPT = (
    "幫我維持服裝設計與角色特徵 生成1張這個角色在不同背景 不同姿勢 不同動作 不同表情 "
    "不同長寬比的一張圖 " + STYLE_TEXT
)
NSFW_TERMS = (
    "nsfw", "nude", "naked", "lingerie", "bikini", "underwear",
    "nipple", "penis", "vagina",
    "裸體", "裸露", "色情", "內衣", "泳裝", "比基尼",
)
PLAN_INSTRUCTIONS = (
    "Use only the provided reference image and the current user's prompt. "
    "Do not generate images. Do not use tools, files, skills, memory, or external information. "
    "Reply with one JSON object and no other text."
)


class PlanMismatch(ValueError):
    """The saved plan does not match this N and must not be redesigned in place."""


def generation_instructions(count=1):
    """One image per call. `count` remains for older callers and is ignored."""
    del count
    return (
        "Use only the provided reference image and the current user's prompt. "
        "Image generation is the only allowed capability. Never use other tools, "
        "files, skills, memory, or external information. "
        "Generate exactly 1 image, not a collage or sheet."
    )


def prepare_home(source, target, model=DEFAULT_MODEL, count=DEFAULT_COUNT, instructions=None):
    """Read only auth/cache from source; create only auth + one-model catalog."""
    target.mkdir(mode=0o700)
    shutil.copy2(source / "auth.json", target / "auth.json")
    (target / "auth.json").chmod(0o600)
    cache = json.loads((source / "models_cache.json").read_text(encoding="utf-8-sig"))
    entry = next((item for item in cache["models"] if item["slug"] == model), None)
    if entry is None:
        raise ValueError(f"Model {model!r} is absent from {source / 'models_cache.json'}")
    text = generation_instructions(count) if instructions is None else instructions
    entry.update(
        input_modalities=["text", "image"],
        base_instructions=text,
        model_messages={
            "instructions_template": text,
            "instructions_variables": None,
            "approvals": None,
        },
        include_skills_usage_instructions=False,
        supports_reasoning_summaries=True,
        supports_parallel_tool_calls=False,
        supports_search_tool=False,
        experimental_supported_tools=[],
        # Cached Sol catalogs can require code mode, whose host is deliberately
        # disabled by the judge. Expose image_gen directly without that host.
        tool_mode="direct",
    )
    catalog = target / "model_catalog.json"
    catalog.write_text(json.dumps({"models": [entry]}), encoding="utf-8")
    return catalog


def isolated_environment(home, source=None):
    source = os.environ if source is None else source
    env = {key: value for key, value in source.items()
           if not key.upper().startswith("CODEX_")}
    env["CODEX_HOME"] = str(home.resolve())
    return env


def command(codex, cwd, catalog, reference, last_message,
            model=DEFAULT_MODEL, effort=DEFAULT_EFFORT, image_generation=True):
    """Mirror the judge, except image generation replaces the scoring schema.

    Planning passes image_generation=False so the same sandbox stays, without
    enabling the image tool. The default argv is unchanged.
    """
    value = [
        codex, "exec", "--json", "--output-last-message", str(last_message),
        "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config",
        "--skip-git-repo-check", "--model", model,
        "-c", f'model_reasoning_effort="{effort}"',
        "-c", 'approval_policy="never"',
        "-c", 'default_permissions="judge"',
        "-c", 'permissions.judge.filesystem={":minimal"="read"}',
        "-c", "permissions.judge.network.enabled=false",
        "-c", "skills.include_instructions=false",
        "-c", "skills.bundled.enabled=false",
        "-c", "include_apps_instructions=false",
        "-c", "include_collaboration_mode_instructions=false",
        "-c", "include_environment_context=false",
        "-c", "include_permissions_instructions=false",
        "-c", 'web_search="disabled"',
        "--sandbox", "danger-full-access",
        "-c", f"model_catalog_json={json.dumps(str(catalog.resolve()))}",
    ]
    for feature in DISABLED_FEATURES:
        if image_generation and feature == "image_generation":
            continue
        value.extend(("--disable", feature))
    if image_generation:
        value.extend(("--enable", "image_generation"))
    value.extend(("-i", str(reference), "-C", str(cwd), "-"))
    return value


def _event_objects(stream):
    """Walk JSONL items, including nested image-generation results."""
    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        yield from walk(event)


def _is_png(data):
    """Check PNG framing and CRCs, rather than renaming JPEG/WebP to .png."""
    if not data.startswith(PNG_SIGNATURE):
        return False
    offset = len(PNG_SIGNATURE)
    seen_header = seen_data = False
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        tag = data[offset + 4:offset + 8]
        end = offset + 8 + size
        if end + 4 > len(data):
            return False
        crc = struct.unpack_from(">I", data, end)[0]
        if zlib.crc32(data[offset + 4:end]) & 0xFFFFFFFF != crc:
            return False
        if not seen_header:
            if tag != b"IHDR" or size != 13:
                return False
            seen_header = True
        if tag == b"IDAT":
            seen_data = True
        if tag == b"IEND":
            return size == 0 and seen_data and end + 4 == len(data)
        offset = end + 4
    return False


def collect_images(home, stream):
    """Collect only this fresh round's home; never follow external event paths."""
    home = home.resolve()
    generated = home / "generated_images"
    paths = sorted(generated.rglob("*")) if generated.is_dir() else []
    objects = list(_event_objects(stream))
    for obj in objects:
        for key in ("savedPath", "saved_path"):
            value = obj.get(key)
            if isinstance(value, str):
                path = Path(value)
                paths.append(path if path.is_absolute() else home / path)

    seen_paths, seen_hashes = set(), set()

    def unique_png(data):
        if not _is_png(data):
            return False
        digest = hashlib.sha256(data).digest()
        if digest in seen_hashes:
            return False
        seen_hashes.add(digest)
        return True

    for path in paths:
        resolved = path.resolve()
        if home not in resolved.parents or resolved in seen_paths or not resolved.is_file():
            continue
        seen_paths.add(resolved)
        data = resolved.read_bytes()
        if unique_png(data):
            yield data

    for obj in objects:
        values = [obj.get("b64_json"), obj.get("image_base64")]
        if obj.get("type") == "image_generation_call":
            values.append(obj.get("result"))
        for value in values:
            if not isinstance(value, str):
                continue
            if value.startswith("data:image/png;base64,"):
                value = value.partition(",")[2]
            try:
                data = base64.b64decode(value, validate=True)
            except (ValueError, binascii.Error):
                continue
            if unique_png(data):
                yield data


def next_number(output):
    numbers = [int(match[1]) for path in output.iterdir()
               if (match := re.fullmatch(r"([0-9]+)\.png", path.name))]
    return max(numbers, default=0) + 1


def existing_images(folder):
    """Valid / invalid PNG files already in folder (any *.png name)."""
    valid, invalid = [], []
    for path in sorted(Path(folder).iterdir()):
        if path.is_file() and path.suffix.lower() == ".png":
            (valid if _is_png(path.read_bytes()) else invalid).append(path)
    return valid, invalid


def update_missing_json(folder, name, missing, last_error, missing_ids=None):
    """Update <parent>/missing.json for one group; delete it when nothing is missing."""
    path = Path(folder).parent / "missing.json"
    if not path.is_file():
        if missing:
            report = {"missing": {name: missing}, "last_errors": {name: last_error}}
            if missing_ids is not None:
                report["missing_ids"] = {name: list(missing_ids)}
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path
    report = json.loads(path.read_text(encoding="utf-8"))
    report.setdefault("missing", {})[name] = missing
    report.setdefault("last_errors", {})[name] = last_error if missing else None
    if missing_ids is not None:
        report.setdefault("missing_ids", {})[name] = list(missing_ids) if missing else []
    if any(report["missing"].values()):
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        path.unlink()
    return path


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def case_slots(n, groups=ALL_GROUPS):
    """Stable ids and filenames. Aspect ratio rotates inside each group."""
    if n < 1:
        raise ValueError("N must be positive")
    order = []
    if KEEP in groups:
        order.append((KEEP, n))
    if CHANGE in groups:
        order.append((CHANGE, 2 * n))
    unknown = [group for group in groups if group not in (KEEP, CHANGE)]
    if unknown:
        raise ValueError(f"unknown group {unknown[0]}")
    cases = []
    for group, count in order:
        prefix = "keep" if group == KEEP else "change"
        for index in range(1, count + 1):
            cases.append({
                "id": f"{prefix}_{index:02d}",
                "group": group,
                "filename": f"{index:02d}.png",
                "aspect_ratio": ASPECT_RATIOS[(index - 1) % len(ASPECT_RATIOS)],
                "outfit": KEEP_OUTFIT if group == KEEP else "",
            })
    return cases


def group_counts(n, groups):
    counts = {}
    for case in case_slots(n, groups):
        counts[case["group"]] = counts.get(case["group"], 0) + 1
    return counts


def assert_sfw(text, case_id):
    folded = text.casefold()
    for term in NSFW_TERMS:
        if term.casefold() in folded:
            raise ValueError(f"{case_id} is not SFW (matched {term})")


def assert_unique(cases):
    for group in {case["group"] for case in cases}:
        rows = [case for case in cases if case["group"] == group and not case.get("legacy_scene")]
        backgrounds, moments = set(), set()
        for case in rows:
            background = case["background"].casefold()
            moment = (case["pose"].casefold(), case["action"].casefold(), case["expression"].casefold())
            if background in backgrounds:
                raise ValueError(f"duplicate background in {group}: {case['id']}")
            if moment in moments:
                raise ValueError(f"duplicate pose/action/expression in {group}: {case['id']}")
            backgrounds.add(background)
            moments.add(moment)
    outfits = [case["outfit"].casefold() for case in cases if case["group"] == CHANGE]
    if len(outfits) != len(set(outfits)):
        raise ValueError("change outfits must be unique")


def _rows_from_designed(designed):
    if isinstance(designed, dict):
        if "cases" in designed:
            return designed["cases"]
        if "scenes" in designed:
            return designed["scenes"]
        raise ValueError("design result needs cases or scenes")
    if isinstance(designed, list):
        return designed
    raise ValueError("design result must be an object or a list")


def assign_cases(n, designed, groups=ALL_GROUPS):
    """Stamp stable ids onto a model plan. Aspect ratio and keep outfit are fixed here."""
    slots = case_slots(n, groups)
    rows = _rows_from_designed(designed)
    if rows and all(isinstance(row, str) for row in rows):
        if tuple(groups) != (KEEP,):
            raise ValueError("a string scene list can only fill keep_outfit")
        if len(rows) != len(slots):
            raise ValueError(f"expected {len(slots)} scenes, got {len(rows)}")
        cases = []
        for slot, text in zip(slots, rows):
            scene = text.strip()
            if not scene:
                raise ValueError(f"{slot['id']} is empty")
            assert_sfw(scene, slot["id"])
            case = dict(slot)
            case["legacy_scene"] = scene
            case["outfit"] = KEEP_OUTFIT
            cases.append(case)
        return {"n": n, "cases": cases}
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("cases must be objects or legacy scene strings")
    if all(str(row.get("id", "")).strip() for row in rows):
        by_id = {}
        for row in rows:
            case_id = str(row["id"]).strip()
            if case_id in by_id:
                raise ValueError(f"duplicate case id {case_id}")
            by_id[case_id] = row
        ordered, missing = [], []
        for slot in slots:
            row = by_id.get(slot["id"])
            if row is None:
                missing.append(slot["id"])
            else:
                ordered.append(row)
        if missing:
            raise ValueError("plan is missing case ids: " + ", ".join(missing))
    else:
        if any(str(row.get("id", "")).strip() for row in rows):
            raise ValueError("either every case has an id, or none do")
        if len(rows) != len(slots):
            raise ValueError(f"expected {len(slots)} cases, got {len(rows)}")
        ordered = rows
    cases = []
    for slot, row in zip(slots, ordered):
        case = dict(slot)
        for field in TEXT_FIELDS:
            value = row.get(field, "")
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{slot['id']} missing {field}")
            value = value.strip()
            assert_sfw(value, slot["id"])
            case[field] = value
        if slot["group"] == CHANGE:
            outfit = row.get("outfit", "")
            if not isinstance(outfit, str) or not outfit.strip():
                raise ValueError(f"{slot['id']} missing outfit")
            outfit = outfit.strip()
            if outfit.casefold() == KEEP_OUTFIT.casefold():
                raise ValueError(f"{slot['id']} must change the outfit")
            assert_sfw(outfit, slot["id"])
            case["outfit"] = outfit
        else:
            case["outfit"] = KEEP_OUTFIT
        cases.append(case)
    assert_unique(cases)
    return {"n": n, "cases": cases}


def validate_case(case, slot):
    if not isinstance(case, dict):
        raise ValueError(f"{slot['id']} is not an object")
    if case.get("group") != slot["group"] or case.get("filename") != slot["filename"]:
        raise ValueError(
            f"{slot['id']} must stay {slot['group']}/{slot['filename']}; the plan is not redesigned")
    ratio = case.get("aspect_ratio") or slot["aspect_ratio"]
    if ratio not in ASPECT_RATIOS:
        raise ValueError(f"{slot['id']} has unsupported aspect_ratio {ratio!r}")
    case["aspect_ratio"] = ratio
    if slot["group"] == KEEP:
        outfit = case.get("outfit")
        if outfit not in (None, "", KEEP_OUTFIT):
            raise ValueError(f"{slot['id']} must keep the reference outfit")
        case["outfit"] = KEEP_OUTFIT
    else:
        outfit = case.get("outfit", "")
        if not isinstance(outfit, str) or not outfit.strip() or outfit.strip().casefold() == KEEP_OUTFIT.casefold():
            raise ValueError(f"{slot['id']} must change the outfit")
        outfit = outfit.strip()
        assert_sfw(outfit, slot["id"])
        case["outfit"] = outfit
    legacy = case.get("legacy_scene")
    if isinstance(legacy, str) and legacy.strip():
        legacy = legacy.strip()
        assert_sfw(legacy, slot["id"])
        case["legacy_scene"] = legacy
        return case
    for field in TEXT_FIELDS:
        value = case.get(field, "")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{slot['id']} missing {field}")
        value = value.strip()
        assert_sfw(value, slot["id"])
        case[field] = value
    return case


def validate_plan(data, n, groups):
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("plan must be an object with a cases list")
    if "n" in data and data["n"] != n:
        raise PlanMismatch(
            f"saved plan was designed for N={data['n']}; this run asked for N={n}. "
            "The saved plan is reused and is not redesigned.")
    slots = case_slots(n, groups)
    relevant = [case for case in data["cases"] if isinstance(case, dict) and case.get("group") in groups]
    found = {case.get("id") for case in relevant}
    expected = {slot["id"] for slot in slots}
    if found != expected:
        raise PlanMismatch(
            f"saved plan does not match N={n} for {', '.join(groups)} "
            f"(found {len(found)} cases, expected {len(expected)}); the plan is not redesigned")
    by_id = {case["id"]: case for case in relevant}
    selected = [validate_case(by_id[slot["id"]], slot) for slot in slots]
    try:
        assert_unique(selected)
    except ValueError as exc:
        raise ValueError(f"saved plan was not redesigned: {exc}") from exc
    rest = [case for case in data["cases"] if not (isinstance(case, dict) and case.get("id") in expected)]
    plan = dict(data)
    plan["n"] = n
    plan["cases"] = selected + rest
    return plan


def coerce_plan(data, n, groups):
    """Return (plan, migrated). String scenes stay in legacy_scene, in order."""
    if not isinstance(data, dict):
        raise ValueError("plan must be a JSON object")
    if "cases" in data:
        return data, False
    scenes = data.get("scenes")
    if isinstance(scenes, list) and scenes and isinstance(scenes[0], str):
        if CHANGE in groups:
            raise ValueError("legacy string scenes cannot supply change_outfit cases")
        return assign_cases(n, data, groups=(KEEP,)), True
    if isinstance(scenes, list) and scenes:
        return assign_cases(n, data, groups=groups), True
    raise ValueError("plan must contain cases or scenes")


def load_plan(path, n, groups):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    data, migrated = coerce_plan(data, n, groups)
    return validate_plan(data, n, groups), migrated


def write_plan(path, plan):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def parse_json_object(text):
    text = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("plan must be a JSON object")
    return data


def plan_prompt(n):
    ids = [case["id"] for case in case_slots(n)]
    return (
        "你是資料集規劃器。不要生成圖片，不要呼叫工具。只回傳一個 JSON 物件，不要加說明文字。\n"
        f"請為參考圖中的角色設計全部 {len(ids)} 個 SFW 案例（keep {n} 張、change {2 * n} 張）。\n"
        "每個案例都要具體到可以單獨重畫：背景、姿勢、動作、表情、鏡頭都要寫清楚。"
        "同一組內背景不可重複，姿勢、動作、表情的組合也不可重複。\n"
        "keep_*：outfit 留空或寫 identical to the reference front view，服裝與參考圖正面相同。\n"
        "change_*：outfit 寫一套具體的 SFW 服裝（顏色、款式、配件），每套都不同，"
        "符合角色氣質，但不要改臉、髮型、瞳色。\n"
        "不要輸出檔名或長寬比。outfit 只寫服裝本身，不要寫禁止事項。\n"
        "JSON 格式：{\"cases\":[{\"id\":\"keep_01\",\"background\":\"...\",\"pose\":\"...\","
        "\"action\":\"...\",\"expression\":\"...\",\"camera\":\"...\",\"outfit\":\"...\"}]}\n"
        "id 必須正好是下列清單，不可增減：\n" + "\n".join(ids)
    )


def case_prompt(case):
    """One Codex image. The script saves the file; the prompt does not name a folder."""
    if case.get("legacy_scene"):
        scene = case["legacy_scene"].strip()
    else:
        scene = (
            f"背景：{case['background']}\n姿勢：{case['pose']}\n動作：{case['action']}\n"
            f"表情：{case['expression']}\n鏡頭：{case['camera']}"
        )
    if case["group"] == KEEP:
        clothing = (
            "服裝必須與參考圖正面完全相同（outfit identical to the reference front view）。"
            "不得改動服裝設計、顏色或配件。"
        )
    else:
        clothing = (
            f"服裝改為：{case['outfit']}。"
            "必須更換服裝，但不得改變角色的臉、髮型、瞳色、體型比例與識別特徵。"
        )
    return (
        "請依照參考圖維持角色特徵，只生成 1 張圖片，不要拼貼、不要多格、不要角色設定集。\n"
        f"案例 {case['id']}，長寬比 {case['aspect_ratio']}。\n"
        f"{scene}\n{clothing}\n{STYLE_TEXT}\n"
        "內容必須是 SFW。"
    )


def grok_image_prompt(case):
    """One Grok image_edit. The caller replaces {reference} with the staged file."""
    if case.get("legacy_scene"):
        scene = case["legacy_scene"].strip()
    else:
        scene = (
            f"背景：{case['background']}；姿勢：{case['pose']}；動作：{case['action']}；"
            f"表情：{case['expression']}；鏡頭：{case['camera']}。"
        )
    return (
        f"{GROK_KEEP_PROMPT}\n{scene}\noutfit identical to the reference front view\n"
        f"案例 {case['id']}，只生成這 1 張，檔名對應 {case['filename']}。\n"
        f'用 image_edit，image=["{{reference}}", "{{reference}}"]，aspect_ratio="{case["aspect_ratio"]}"。'
        "一次產生一張；必須檢視結果並與參考正面比較，若服裝走樣則重新生成該張，"
        "回報最終 session 圖片絕對路徑 output_file。"
        "遇工具拒絕則記錄失敗，不改寫要求繞過限制。"
    )


def case_selected(case, only):
    keys = {case["id"], case["filename"], f"{case['group']}/{case['filename']}"}
    return any(item in keys for item in only)


def select_cases(cases, groups, target=None, only=None):
    pool = [case for case in cases if case["group"] in groups]
    if only:
        matched = [case for case in pool if case_selected(case, only)]
        if not matched:
            raise ValueError("--only did not match any planned case: " + ", ".join(sorted(only)))
        return matched
    if target is not None:
        if len(tuple(groups)) != 1:
            raise ValueError("--target applies to a single outfit group")
        group = next(iter(groups))
        if target > len(pool):
            raise ValueError(f"--target {target} exceeds {len(pool)} {group} cases in the plan")
        return pool[:target]
    return pool


def _valid_png(path):
    path = Path(path)
    return path.is_file() and _is_png(path.read_bytes())


def group_status(cases, output_for):
    status, grouped = {}, {}
    for case in cases:
        grouped.setdefault(case["group"], []).append(case)
    for group, group_cases in grouped.items():
        directory = output_for(group_cases[0]).parent
        planned = {case["filename"] for case in group_cases}
        valid, invalid = existing_images(directory) if directory.is_dir() else ([], [])
        valid_names = {path.name for path in valid}
        status[group] = {
            "existing_valid": sum(1 for name in valid_names if name in planned),
            "existing_invalid": [path.name for path in invalid],
            "extra_png": [path.name for path in valid if path.name not in planned],
            "missing": [case["id"] for case in group_cases if case["filename"] not in valid_names],
        }
    return status


def _directory_hashes(directory, cache):
    directory = Path(directory)
    key = str(directory)
    if key not in cache:
        found = set()
        if directory.is_dir():
            for path in existing_images(directory)[0]:
                found.add(hashlib.sha256(path.read_bytes()).digest())
        cache[key] = found
    return cache[key]


def generate_cases(cases, output_for, reference, generator, max_rounds, log):
    """Return (written_paths, errors_by_id, attempts). Does not overwrite a valid PNG."""
    written, errors, attempts = [], {}, []
    pending = list(cases)
    hashes = {}
    for round_no in range(1, max_rounds + 1):
        if not pending:
            break
        failed = []
        for case in pending:
            dest = Path(output_for(case))
            if _valid_png(dest):
                attempts.append({"id": case["id"], "round": round_no, "ok": True, "error": None})
                continue
            log(f"{case['id']}: round {round_no}/{max_rounds}")
            try:
                if dest.is_file():
                    dest.unlink()
                data = generator(reference, case, dest)
                if not isinstance(data, (bytes, bytearray)) or not _is_png(bytes(data)):
                    raise ValueError("generator did not return a PNG")
                data = bytes(data)
                digest = hashlib.sha256(data).digest()
                if digest in _directory_hashes(dest.parent, hashes):
                    raise ValueError("sha256 duplicate image discarded")
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("xb") as handle:
                    handle.write(data)
                _directory_hashes(dest.parent, hashes).add(digest)
                written.append(dest)
                errors.pop(case["id"], None)
                attempts.append({"id": case["id"], "round": round_no, "ok": True, "error": None})
                log(f"{case['id']}: saved {dest}")
            except FileExistsError:
                if _valid_png(dest):
                    attempts.append({"id": case["id"], "round": round_no, "ok": True, "error": None})
                    continue
                message = "could not create output"
                errors[case["id"]] = message
                failed.append(case)
                attempts.append({"id": case["id"], "round": round_no, "ok": False, "error": message})
            except (OSError, ValueError, RuntimeError) as exc:
                errors[case["id"]] = str(exc)
                failed.append(case)
                attempts.append({"id": case["id"], "round": round_no, "ok": False, "error": str(exc)})
                log(f"{case['id']}: {exc}")
        pending = failed
    return written, errors, attempts


def _scope_cases(cases, groups, target, chosen):
    base = select_cases(cases, groups, target=target, only=None)
    seen, scope = set(), []
    for case in list(base) + list(chosen):
        if case["id"] not in seen:
            seen.add(case["id"])
            scope.append(case)
    return scope


def _record_missing(scope, output_for, errors):
    missing = {}
    grouped = {}
    for case in scope:
        grouped.setdefault(case["group"], []).append(case)
    for group, group_cases in grouped.items():
        absent = [case for case in group_cases if not _valid_png(output_for(case))]
        ids = [case["id"] for case in absent]
        last = None
        for case in absent:
            if case["id"] in errors:
                last = errors[case["id"]]
        if ids and last is None:
            last = f"{len(ids)} planned image(s) still missing"
        update_missing_json(output_for(group_cases[0]).parent, group, len(ids), last, ids)
        missing[group] = ids
    return missing


def run_case_generation(*, n, cases_file, plan_groups, generate_groups, output_for, reference,
                        designer, generator, dry_run=False, design_only=False, only=None,
                        max_rounds=DEFAULT_MAX_ROUNDS, target=None, log=None):
    """Design the full plan once, then generate each selected case that lacks a valid PNG."""
    if max_rounds < 1:
        raise ValueError("max-rounds must be positive")
    cases_file = Path(cases_file)
    log = log or (lambda message: print(message, file=sys.stderr, flush=True))
    only_set = set(only) if only else None
    plan, status, migrated = None, "missing", False
    if cases_file.is_file():
        plan, migrated = load_plan(cases_file, n, plan_groups)
        status = "reuse"
        if migrated and not dry_run:
            write_plan(cases_file, plan)
    elif not dry_run:
        reference = require_reference(reference)
        if designer is None:
            raise ValueError("no designer")
        plan = validate_plan(designer(reference, n), n, plan_groups)
        write_plan(cases_file, plan)
        status = "designed"
    catalog = plan["cases"] if plan else case_slots(n, plan_groups)
    chosen = select_cases(catalog, generate_groups, target=None if only_set else target, only=only_set)
    pending = [case for case in chosen if not _valid_png(output_for(case))]
    report = {
        "status": status,
        "cases_file": str(cases_file),
        "n": n,
        "dry_run": dry_run,
        "design_only": design_only,
        "migrated": migrated and not dry_run,
        "reference": str(reference),
        "would_design": None if plan else group_counts(n, plan_groups),
        "target": target,
        "only": sorted(only_set) if only_set else None,
        "aspect_ratios": list(ASPECT_RATIOS),
        "groups": group_status(_scope_cases(catalog, generate_groups, target, chosen), output_for),
        "to_generate": [case["id"] for case in pending],
        "cases": None if plan is None else [case for case in plan["cases"] if case["id"] in {item["id"] for item in pending}],
    }
    if dry_run or design_only:
        report["remaining"] = report["to_generate"]
        report["written"] = []
        return {"exit_code": 0, "status": status, "cases_file": str(cases_file),
                "written": [], "missing": {group: info["missing"] for group, info in report["groups"].items()},
                "attempts": [], "report": report}
    written, errors, attempts = ([], {}, [])
    if pending:
        reference = require_reference(reference)
        written, errors, attempts = generate_cases(
            pending, output_for, reference, generator, max_rounds, log)
    scope = _scope_cases(catalog, generate_groups, target, chosen)
    missing = _record_missing(scope, output_for, errors)
    report["groups"] = group_status(scope, output_for)
    report["remaining"] = [case_id for ids in missing.values() for case_id in ids]
    report["written"] = [str(path) for path in written]
    report["cases"] = None if plan is None else [
        case for case in plan["cases"] if case["id"] in set(report["remaining"])]
    return {"exit_code": int(bool(report["remaining"])), "status": status,
            "cases_file": str(cases_file), "written": report["written"], "missing": missing,
            "attempts": attempts, "report": report}


def require_reference(path):
    path = Path(path).expanduser()
    if not path.is_file():
        raise ValueError(f"Reference must be an image file: {path}")
    return path.resolve()


@dataclass
class CodexCall:
    returncode: object
    images: list
    last_message: str
    error: str


def run_codex_once(reference, prompt, *, instructions, image_generation, model, effort, timeout, codex):
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    reference = require_reference(reference)
    executable = shutil.which(codex)
    if not executable:
        raise ValueError(f"Codex executable not found: {codex}")
    executable = str(Path(executable).resolve())
    source_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    with tempfile.TemporaryDirectory(prefix="codex-batch-image-") as temporary:
        root = Path(temporary)
        home, cwd = root / "home", root / "work"
        catalog = prepare_home(source_home, home, model, instructions=instructions)
        cwd.mkdir()
        attached = cwd / ("reference" + reference.suffix.lower())
        shutil.copyfile(reference, attached)
        error = None
        try:
            run = subprocess.run(
                command(executable, cwd, catalog, attached, root / "last-message.txt",
                        model=model, effort=effort, image_generation=image_generation),
                input=prompt, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", timeout=timeout, check=False,
                cwd=str(cwd), env=isolated_environment(home),
            )
            stdout, stderr, returncode = run.stdout, run.stderr, run.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout or "", exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            returncode = None
            error = f"Codex timed out after {timeout} seconds: {(stderr or stdout or 'no output').strip()[-2000:]}"
        images = list(collect_images(home, stdout)) if image_generation else []
        last_path = root / "last-message.txt"
        last_message = last_path.read_text(encoding="utf-8-sig") if last_path.is_file() else ""
        if returncode:
            error = f"Codex failed with exit code {returncode}: {(stderr or stdout or 'no output').strip()[-2000:]}"
        elif returncode == 0 and image_generation and not images:
            error = f"No PNG images returned: {(last_message or stderr or stdout).strip()[-2000:]}"
        elif returncode == 0 and not image_generation and not last_message.strip():
            error = f"No JSON plan returned: {(stderr or stdout or 'no output').strip()[-2000:]}"
        return CodexCall(returncode, images, last_message, error)


def codex_designer(args, codex="codex"):
    def designer(reference, n):
        last = None
        prompt = plan_prompt(n)
        for attempt in range(1, args.max_rounds + 1):
            print(f"Planning attempt {attempt}/{args.max_rounds}: {n} keep + {2 * n} change",
                  file=sys.stderr, flush=True)
            try:
                call = run_codex_once(
                    reference, prompt, instructions=PLAN_INSTRUCTIONS, image_generation=False,
                    model=args.model, effort=args.effort, timeout=args.plan_timeout, codex=codex)
                if call.error and not call.last_message.strip():
                    raise RuntimeError(call.error)
                return assign_cases(n, parse_json_object(call.last_message))
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                last = exc
                print(f"Planning failed: {exc}", file=sys.stderr, flush=True)
        raise RuntimeError(f"Could not design cases after {args.max_rounds} attempts: {last}")
    return designer


def codex_generator(args, codex="codex"):
    def generator(reference, case, dest):
        del dest
        call = run_codex_once(
            reference, case_prompt(case), instructions=generation_instructions(),
            image_generation=True, model=args.model, effort=args.effort,
            timeout=args.timeout, codex=codex)
        if not call.images:
            raise RuntimeError(call.error or "No PNG images returned")
        return call.images[0]
    return generator


def _emit(result, stream):
    print(json.dumps(result["report"], ensure_ascii=False), file=stream, flush=True)
    for path in result["written"]:
        print(path)
    if result["exit_code"]:
        missing = Path(result["cases_file"]).parent / "missing.json"
        print(f"Error: {sum(len(ids) for ids in result['missing'].values())} image(s) still missing; see {missing}",
              file=sys.stderr, flush=True)
    return result["exit_code"]


def add_run_arguments(parser):
    parser.add_argument("--cases", type=Path, help="Case plan JSON (default: <codex dir>/cases.json)")
    parser.add_argument("--max-rounds", type=positive_int, default=DEFAULT_MAX_ROUNDS)
    parser.add_argument("--timeout", type=positive_int, default=DEFAULT_TIMEOUT,
                        help="Seconds for one image call")
    parser.add_argument("--plan-timeout", type=positive_int, default=DEFAULT_PLAN_TIMEOUT,
                        help="Seconds for the planning call")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the plan and missing case ids; do not call Codex")
    parser.add_argument("--design-only", action="store_true",
                        help="Write cases.json and stop before any image")
    parser.add_argument("--only", nargs="+",
                        help="Generate these case ids or filenames only, e.g. change_02 or keep_outfit/01.png")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default=DEFAULT_EFFORT)


def main_fill(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fill-existing", type=Path, nargs="?", const=True, required=True,
                        help="Existing change_outfit folder to top up")
    parser.add_argument("--target", type=positive_int, required=True,
                        help="How many change cases to complete, from change_01 (default 2N with --workspace)")
    parser.add_argument("--reference", type=Path, required=True, help="Character sheet image path")
    parser.add_argument("n", type=positive_int, nargs="?", default=DEFAULT_COUNT,
                        help="Plan size N: keep N and change 2N (default 30)")
    add_run_arguments(parser)
    args = parse_args(parser, "fill", argv)
    try:
        folder = Path(args.fill_existing).expanduser().resolve()
        if folder.exists() and not folder.is_dir():
            raise ValueError(f"Not a directory: {folder}")
        result = run_case_generation(
            n=args.n, cases_file=args.cases or folder.parent / "cases.json",
            plan_groups=ALL_GROUPS, generate_groups=(CHANGE,),
            output_for=lambda case: folder / case["filename"], reference=args.reference,
            designer=codex_designer(args), generator=codex_generator(args),
            dry_run=args.dry_run, design_only=args.design_only, only=args.only,
            max_rounds=args.max_rounds, target=args.target)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Error: {error}\n")
    return _emit(result, sys.stderr)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if any(item == "--fill-existing" or str(item).startswith("--fill-existing=") for item in argv):
        return main_fill(argv)
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("n", type=positive_int, nargs="?", default=DEFAULT_COUNT,
                        help="keep N images and change 2N images (default 30)")
    parser.add_argument("reference", type=Path, help="Character sheet image path")
    parser.add_argument("folder", type=Path, help="Codex output folder (parent of keep_outfit and change_outfit)")
    add_run_arguments(parser)
    args = parse_args(parser, "generate", argv)
    try:
        folder = Path(args.folder).expanduser().resolve()
        result = run_case_generation(
            n=args.n, cases_file=args.cases or folder / "cases.json",
            plan_groups=ALL_GROUPS, generate_groups=ALL_GROUPS,
            output_for=lambda case: folder / case["group"] / case["filename"],
            reference=args.reference, designer=codex_designer(args), generator=codex_generator(args),
            dry_run=args.dry_run, design_only=args.design_only, only=args.only,
            max_rounds=args.max_rounds)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Error: {error}\n")
    return _emit(result, sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
