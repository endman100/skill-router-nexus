from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


ROUTER_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = ROUTER_DIR.parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdapterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paraformer = load_module(
            "asr_router_paraformer", ROUTER_DIR / "scripts" / "paraformer_asr.py"
        )
        cls.seed = load_module(
            "asr_router_seed", ROUTER_DIR / "scripts" / "seed_asr.py"
        )

    def test_paraformer_millisecond_fields_are_always_converted(self) -> None:
        payload = {
            "sentences": [
                {"text": "短句", "begin_time": 100, "end_time": 900},
            ]
        }
        self.assertEqual(
            self.paraformer.collect_segments(payload),
            [{"text": "短句", "start": 0.1, "end": 0.9}],
        )

    def test_seed_normalizer_uses_router_provider_id_and_contract_fields(self) -> None:
        raw = {
            "result": {
                "text": "你好",
                "language": "zh-CN",
                "utterances": [
                    {
                        "text": "你好",
                        "start_time": 0,
                        "end_time": 500,
                        "words": [
                            {"text": "你", "start_time": 0, "end_time": 200},
                            {"text": "好", "start_time": 200, "end_time": 500},
                        ],
                    }
                ],
            }
        }
        result = self.seed.normalize_volcengine_result(
            raw,
            "volc.seedasr.auc",
            source="sample.wav",
            raw_artifact="raw.json",
            command="python seed_asr.py sample.wav",
            source_sha256="abc123",
        )
        self.assertEqual(result["provider"], "seed-asr")
        self.assertEqual(result["language"], "zh-CN")
        self.assertEqual(result["raw_artifact"], "raw.json")
        self.assertEqual(result["command"], "python seed_asr.py sample.wav")
        self.assertEqual(result["source_sha256"], "abc123")


class SingleSourceTests(unittest.TestCase):
    def test_business_scripts_do_not_execute_router_adapters_directly(self) -> None:
        forbidden = {
            "seed_asr.py",
            "paraformer_asr.py",
            "qwen3_asr.py",
            "openai_whisper_api.sh",
        }
        violations: list[str] = []
        roots = [REPO_ROOT / name for name in ("Speech-Recognition", "Video-Editing", "Video-Generation")]
        for root in roots:
            for directory, dirnames, filenames in os.walk(root):
                dirnames[:] = [
                    name for name in dirnames
                    if name not in {"tests", "node_modules", ".git", "__pycache__"}
                ]
                path_root = Path(directory)
                if ROUTER_DIR == path_root or ROUTER_DIR in path_root.parents:
                    dirnames[:] = []
                    continue
                for filename in filenames:
                    path = path_root / filename
                    if path.suffix.lower() not in {".py", ".sh", ".js"}:
                        continue
                    try:
                        content = path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        continue
                    matched = sorted(name for name in forbidden if name in content)
                    if matched:
                        violations.append(
                            f"{path.relative_to(REPO_ROOT)}: {', '.join(matched)}"
                        )
        self.assertEqual(violations, [], "\n".join(violations))

    def test_schema_links_resolve(self) -> None:
        schema = (ROUTER_DIR / "references" / "schema.md").read_text(encoding="utf-8")
        links = []
        for token in schema.split("(")[1:]:
            target = token.split(")", 1)[0]
            if target.endswith(".md"):
                links.append(target)
        missing = [target for target in links if not (ROUTER_DIR / "references" / target).is_file()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
