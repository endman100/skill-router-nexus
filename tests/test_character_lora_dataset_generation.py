"""Plan-then-one-image flow for character LoRA dataset generation."""
import json
import struct
import subprocess
import sys
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "AI-Training" / "character-lora-training"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import codex_batch_image_gen as gen  # noqa: E402


def tiny_png(red):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes([0, red, 10, 20])))
            + chunk(b"IEND", b""))


def designed(n, groups=gen.ALL_GROUPS):
    rows = []
    for case in gen.case_slots(n, groups):
        row = {field: f"{field}-{case['id']}" for field in gen.TEXT_FIELDS}
        row["id"] = case["id"]
        row["outfit"] = (f"wool coat {case['id']}" if case["group"] == gen.CHANGE else gen.KEEP_OUTFIT)
        rows.append(row)
    return gen.assign_cases(n, {"cases": rows}, groups)


class PlanTests(unittest.TestCase):
    def test_slots_are_stable_and_rotate_aspect(self):
        cases = gen.case_slots(2)
        self.assertEqual([case["id"] for case in cases],
                         ["keep_01", "keep_02", "change_01", "change_02", "change_03", "change_04"])
        self.assertEqual([case["filename"] for case in cases if case["group"] == gen.CHANGE],
                         ["01.png", "02.png", "03.png", "04.png"])
        self.assertEqual(cases[0]["aspect_ratio"], "1:1")
        self.assertEqual(cases[4]["aspect_ratio"], "3:4")  # change_03
        self.assertEqual(cases[5]["aspect_ratio"], "16:9")  # change_04
        self.assertEqual(cases[0]["outfit"], gen.KEEP_OUTFIT)
        self.assertTrue(all(case["outfit"] == "" for case in cases if case["group"] == gen.CHANGE))

    def test_assign_rejects_nsfw_and_duplicate_outfits(self):
        plan = designed(1)
        self.assertEqual(plan["n"], 1)
        self.assertEqual(len(plan["cases"]), 3)
        bad = designed(1)
        bad_rows = []
        for case in bad["cases"]:
            row = {field: case[field] for field in gen.TEXT_FIELDS}
            row["id"] = case["id"]
            row["outfit"] = "red bikini" if case["group"] == gen.CHANGE else gen.KEEP_OUTFIT
            bad_rows.append(row)
        with self.assertRaises(ValueError):
            gen.assign_cases(1, {"cases": bad_rows})
        dup = designed(1)
        rows = []
        for case in dup["cases"]:
            row = {field: case[field] for field in gen.TEXT_FIELDS}
            row["id"] = case["id"]
            row["outfit"] = "same coat" if case["group"] == gen.CHANGE else gen.KEEP_OUTFIT
            rows.append(row)
        with self.assertRaises(ValueError):
            gen.assign_cases(1, {"cases": rows})

    def test_legacy_scenes_keep_order_and_text(self):
        plan, migrated = gen.coerce_plan({"scenes": ["屋頂黃昏", "車站月台"]}, 2, (gen.KEEP,))
        plan = gen.validate_plan(plan, 2, (gen.KEEP,))
        self.assertTrue(migrated)
        self.assertEqual([case["id"] for case in plan["cases"]], ["keep_01", "keep_02"])
        self.assertEqual(plan["cases"][1]["legacy_scene"], "車站月台")
        self.assertEqual(plan["cases"][1]["filename"], "02.png")
        self.assertEqual(plan["cases"][1]["outfit"], gen.KEEP_OUTFIT)

    def test_prompts_are_one_image_and_isolated_commands_differ(self):
        case = designed(1)["cases"][0]
        change = next(item for item in designed(1)["cases"] if item["group"] == gen.CHANGE)
        keep_prompt = gen.case_prompt(case)
        change_prompt = gen.case_prompt(change)
        self.assertIn("只生成 1 張", keep_prompt)
        self.assertIn(gen.KEEP_OUTFIT, keep_prompt)
        self.assertIn(change["outfit"], change_prompt)
        self.assertIn("必須更換服裝", change_prompt)
        self.assertNotIn("生成N張", keep_prompt + change_prompt)
        self.assertNotIn("Generate N images", keep_prompt + change_prompt)
        grok_prompt = gen.grok_image_prompt(case)
        self.assertIn('image=["{reference}", "{reference}"]', grok_prompt)
        self.assertIn(f'aspect_ratio="{case["aspect_ratio"]}"', grok_prompt)
        self.assertIn(case["id"], grok_prompt)
        self.assertIn("keep_01", gen.plan_prompt(1))
        self.assertIn("change_02", gen.plan_prompt(1))
        self.assertIn("不要生成圖片", gen.plan_prompt(1))
        source = (SCRIPTS / "codex_batch_image_gen.py").read_text(encoding="utf-8")
        self.assertNotIn("Generate N images", source)
        self.assertNotIn("生成N張", source)

        argv = gen.command("codex", Path("/work"), Path("/catalog.json"), Path("/ref.png"), Path("/last.txt"))
        self.assertEqual(argv, gen.command(
            "codex", Path("/work"), Path("/catalog.json"), Path("/ref.png"), Path("/last.txt"),
            image_generation=True))
        self.assertEqual(argv[-7:], [
            "--enable", "image_generation", "-i", "/ref.png", "-C", "/work", "-"])
        disabled = [argv[index + 1] for index, item in enumerate(argv) if item == "--disable"]
        self.assertIn("shell_tool", disabled)
        self.assertNotIn("image_generation", disabled)
        self.assertIn("danger-full-access", argv)
        self.assertIn("permissions.judge.network.enabled=false", argv)
        quiet = gen.command(
            "codex", Path("/work"), Path("/catalog.json"), Path("/ref.png"), Path("/last.txt"),
            image_generation=False)
        quiet_disabled = [quiet[index + 1] for index, item in enumerate(quiet) if item == "--disable"]
        self.assertIn("image_generation", quiet_disabled)
        self.assertNotIn("--enable", quiet)
        self.assertIn("-i", quiet)
        self.assertIn("danger-full-access", quiet)

    def test_run_designs_once_then_fills_only_missing_ids(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = root / "sheet.png"
            reference.write_bytes(tiny_png(1))
            folder = root / "codex"
            cases_file = folder / "cases.json"
            calls = []

            def designer(path, n):
                calls.append("design")
                self.assertEqual(path, reference.resolve())
                return designed(n)

            def generator(path, case, dest):
                del path, dest
                calls.append(case["id"])
                return tiny_png(10 + len(calls))

            result = gen.run_case_generation(
                n=1, cases_file=cases_file, plan_groups=gen.ALL_GROUPS, generate_groups=gen.ALL_GROUPS,
                output_for=lambda case: folder / case["group"] / case["filename"], reference=reference,
                designer=designer, generator=generator, max_rounds=2, log=lambda message: None)
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(calls, ["design", "keep_01", "change_01", "change_02"])
            self.assertTrue((folder / "keep_outfit" / "01.png").is_file())
            self.assertEqual(json.loads(cases_file.read_text(encoding="utf-8"))["n"], 1)
            saved = cases_file.read_bytes()

            def boom(path, n):
                del path, n
                raise AssertionError("plan was redesigned")

            again = gen.run_case_generation(
                n=1, cases_file=cases_file, plan_groups=gen.ALL_GROUPS, generate_groups=gen.ALL_GROUPS,
                output_for=lambda case: folder / case["group"] / case["filename"], reference=reference,
                designer=boom, generator=generator, log=lambda message: None)
            self.assertEqual(again["exit_code"], 0)
            self.assertEqual(again["written"], [])
            self.assertEqual(cases_file.read_bytes(), saved)

            target = folder / "change_outfit" / "02.png"
            target.unlink()
            calls.clear()
            partial = gen.run_case_generation(
                n=1, cases_file=cases_file, plan_groups=gen.ALL_GROUPS, generate_groups=gen.ALL_GROUPS,
                output_for=lambda case: folder / case["group"] / case["filename"], reference=reference,
                designer=boom, generator=generator, only=["change_02"], log=lambda message: None)
            self.assertEqual(calls, ["change_02"])
            self.assertEqual(partial["exit_code"], 0)
            self.assertTrue(target.is_file())

            with self.assertRaises(gen.PlanMismatch):
                gen.run_case_generation(
                    n=2, cases_file=cases_file, plan_groups=gen.ALL_GROUPS, generate_groups=gen.ALL_GROUPS,
                    output_for=lambda case: folder / case["group"] / case["filename"], reference=reference,
                    designer=boom, generator=generator, dry_run=True, log=lambda message: None)
            self.assertEqual(cases_file.read_bytes(), saved)

    def test_invalid_png_is_replaced_and_duplicate_is_not(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = root / "sheet.png"
            reference.write_bytes(tiny_png(2))
            folder = root / "out"
            keep = folder / "keep_outfit"
            keep.mkdir(parents=True)
            (keep / "note.png").write_bytes(tiny_png(9))
            plan = designed(1, (gen.KEEP,))
            cases_file = folder / "cases.json"
            gen.write_plan(cases_file, plan)

            def generator(path, case, dest):
                del path, dest
                return tiny_png(9)

            result = gen.run_case_generation(
                n=1, cases_file=cases_file, plan_groups=(gen.KEEP,), generate_groups=(gen.KEEP,),
                output_for=lambda case: folder / case["group"] / case["filename"], reference=reference,
                designer=None, generator=generator, max_rounds=1, log=lambda message: None)
            self.assertEqual(result["exit_code"], 1)
            self.assertFalse((keep / "01.png").exists())
            missing = json.loads((folder / "missing.json").read_text(encoding="utf-8"))
            self.assertEqual(missing["missing_ids"]["keep_outfit"], ["keep_01"])
            self.assertIn("duplicate", missing["last_errors"]["keep_outfit"])

            (keep / "01.png").write_bytes(b"not a png")

            def fresh(path, case, dest):
                del path, dest
                return tiny_png(40)

            replaced = gen.run_case_generation(
                n=1, cases_file=cases_file, plan_groups=(gen.KEEP,), generate_groups=(gen.KEEP,),
                output_for=lambda case: folder / case["group"] / case["filename"], reference=reference,
                designer=None, generator=fresh, max_rounds=1, log=lambda message: None)
            self.assertEqual(replaced["exit_code"], 0)
            self.assertTrue(gen._is_png((keep / "01.png").read_bytes()))
            self.assertFalse((folder / "missing.json").exists())

    def test_fill_and_legacy_dry_run(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            change = root / "change_outfit"
            change.mkdir()
            cases_file = root / "cases.json"
            gen.write_plan(cases_file, designed(1))
            reference = root / "sheet.png"
            reference.write_bytes(tiny_png(3))
            preview = gen.run_case_generation(
                n=1, cases_file=cases_file, plan_groups=gen.ALL_GROUPS, generate_groups=(gen.CHANGE,),
                output_for=lambda case: change / case["filename"], reference=reference,
                designer=None, generator=None, dry_run=True, target=1, log=lambda message: None)
            self.assertEqual(preview["report"]["to_generate"], ["change_01"])
            self.assertEqual(preview["exit_code"], 0)

            legacy = root / "scenes.json"
            original = json.dumps({"scenes": ["圖書館", "海邊歩道"]}, ensure_ascii=False)
            legacy.write_text(original, encoding="utf-8")
            dry = gen.run_case_generation(
                n=2, cases_file=legacy, plan_groups=(gen.KEEP,), generate_groups=(gen.KEEP,),
                output_for=lambda case: root / "keep" / case["filename"], reference=reference,
                designer=None, generator=None, dry_run=True, log=lambda message: None)
            self.assertEqual(legacy.read_text(encoding="utf-8"), original)
            self.assertEqual(dry["report"]["to_generate"], ["keep_01", "keep_02"])
            migrated = gen.run_case_generation(
                n=2, cases_file=legacy, plan_groups=(gen.KEEP,), generate_groups=(gen.KEEP,),
                output_for=lambda case: root / "keep" / case["filename"], reference=reference,
                designer=None, generator=None, design_only=True, log=lambda message: None)
            self.assertEqual(migrated["exit_code"], 0)
            saved = json.loads(legacy.read_text(encoding="utf-8"))
            self.assertEqual(saved["cases"][0]["legacy_scene"], "圖書館")
            self.assertEqual(saved["cases"][0]["id"], "keep_01")


class CliTests(unittest.TestCase):
    def test_dry_run_does_not_write_a_plan_or_call_a_model(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "demo"
            env = Path(temporary) / "env"
            subprocess.run(
                [sys.executable, "-B", "scripts/ws.py", "create", "--workspace", str(workspace),
                 "--work", "示例", "--character", "角色", "--trigger", "demo_role", "--env", str(env)],
                cwd=SKILL, check=True, capture_output=True, text=True)
            codex = subprocess.run(
                [sys.executable, "-B", "scripts/codex_batch_image_gen.py", "--workspace", str(workspace),
                 "2", "--dry-run"],
                cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(codex.returncode, 0, codex.stderr)
            report = json.loads(codex.stderr)
            self.assertEqual(report["status"], "missing")
            self.assertEqual(report["would_design"], {"keep_outfit": 2, "change_outfit": 4})
            self.assertEqual(report["to_generate"], ["keep_01", "keep_02", "change_01", "change_02", "change_03", "change_04"])
            self.assertFalse((workspace / "04_generate" / "codex" / "cases.json").exists())

            default_n = subprocess.run(
                [sys.executable, "-B", "scripts/codex_batch_image_gen.py", "--workspace", str(workspace),
                 "--dry-run"],
                cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(default_n.returncode, 0, default_n.stderr)
            self.assertEqual(json.loads(default_n.stderr)["would_design"],
                             {"keep_outfit": 30, "change_outfit": 60})

            fill = subprocess.run(
                [sys.executable, "-B", "scripts/codex_batch_image_gen.py", "--workspace", str(workspace),
                 "2", "--fill-existing", "--dry-run"],
                cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(fill.returncode, 0, fill.stderr)
            fill_report = json.loads(fill.stderr)
            self.assertEqual(fill_report["target"], 4)
            self.assertTrue(all(item.startswith("change_") for item in fill_report["to_generate"]))
            self.assertEqual(len(fill_report["to_generate"]), 4)

            grok = subprocess.run(
                [sys.executable, "-B", "scripts/grok_batch_image_gen.py", "--workspace", str(workspace),
                 "2", "--dry-run"],
                cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(grok.returncode, 0, grok.stderr)
            grok_report = json.loads(grok.stdout)
            self.assertEqual(grok_report["would_design"], {"keep_outfit": 2})
            self.assertEqual(grok_report["to_generate"], ["keep_01", "keep_02"])
            self.assertFalse((workspace / "04_generate" / "grok" / "scenes.json").exists())
            grok_default = subprocess.run(
                [sys.executable, "-B", "scripts/grok_batch_image_gen.py", "--workspace", str(workspace),
                 "--dry-run"],
                cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(grok_default.returncode, 0, grok_default.stderr)
            self.assertEqual(json.loads(grok_default.stdout)["would_design"], {"keep_outfit": 30})


if __name__ == "__main__":
    unittest.main()
