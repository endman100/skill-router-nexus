"""Workspace metadata, documented paths, and CLI defaults for training and release."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
DIRECTORIES = (
    "01_collect/codex", "01_collect/grok", "01_collect/reference",
    "02_clean/grok_clean", "02_clean/collected_sfw", "02_clean/collected_nsfw", "03_sheet",
    "04_generate/codex/keep_outfit", "04_generate/codex/change_outfit", "04_generate/grok/keep_outfit",
    "05_caption/vocab", "05_caption/train_set", "06_train", "07_validate/prompts",
    "08_release",
)
FIELDS = ("work", "character", "trigger", "env", "main_outfit_id")


class Workspace:
    def __init__(self, path):
        self.root = Path(path).expanduser().resolve()
        self.file = self.root / "project.json"
        if not self.file.is_file():
            raise ValueError(f"Missing workspace file: {self.file}")
        self.project = json.loads(self.file.read_text("utf-8"))
        for field in FIELDS:
            if field not in self.project or (field != "main_outfit_id" and not self.project[field]):
                raise ValueError(f"Missing required field '{field}' in {self.file}")
        self.env = Path(self.project["env"])

    def path(self, relative):
        return self.root / relative

    def params(self):
        dest = self.path("05_caption/vocab/caption_vocab_params.json")
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(TEMPLATES / dest.name, dest)
        return dest

    def set_main_outfit(self, outfit):
        self.project["main_outfit_id"] = outfit
        self.file.write_text(json.dumps(self.project, ensure_ascii=False, indent=2) + "\n", "utf-8")

    def defaults(self, step, nsfw=False):
        p, e, meta = self.path, self.env, self.project
        query = f"{meta['work']} {meta['character']}"
        images = p("05_caption/images")
        vocab = p("05_caption/vocab")
        resized = p("05_caption/resized")
        groups = [
            ("collected", p("02_clean/collected_sfw")),
            ("collected_nsfw", p("02_clean/collected_nsfw")),
            ("gen_codex_keep", p("04_generate/codex/keep_outfit")),
            ("gen_grok_keep", p("04_generate/grok/keep_outfit")),
            ("gen_codex_change", p("04_generate/codex/change_outfit")),
        ]
        captions = p("05_caption/captions_nsfw" if nsfw else "05_caption/captions")
        if step == "grok_collect":
            return dict(query=query, out=p("01_collect/grok"))
        if step == "grok_clean":
            return dict(target=query, nsfw=p("02_clean/nsfw"), sfw=p("02_clean/sfw"),
                        sheet=p("03_sheet/character-sheet.png"),
                        codex_clean=p("02_clean/codex_clean"), out=p("02_clean/grok_clean"),
                        collected_sfw=p("02_clean/collected_sfw"), collected_nsfw=p("02_clean/collected_nsfw"))
        if step == "grok_generate":
            return dict(reference=p("03_sheet/character-sheet.png"), out=p("04_generate/grok"))
        if step == "grok_vocab":
            return dict(project_dir=self.root, out=vocab, images=images, manifest=images / "manifest.json", params=self.params)
        if step == "grok_caption":
            return dict(project_dir=self.root, images=p("05_caption/images_nsfw"),
                        out=p("05_caption/captions_nsfw"), final_dir=p("05_caption/train_set"),
                        manifest=images / "manifest.json")
        if step == "grok_upscale":
            return dict(out_dir=resized / "_up_grok/collected_nsfw",
                        images=sorted((resized / "_needs_upscale/collected_nsfw").glob("*.png")))
        if step == "collect":
            return dict(query=query, save_dir=p("01_collect"))
        if step == "dedup":
            return dict(out=p("02_clean"), sources=[f"{n}={p('01_collect/' + n)}" for n in ("codex", "grok", "reference")],
                        model_dir=str(e / "models/wd-eva02-large-tagger-v3"))
        if step == "clean":
            return dict(target=query, input_dir=p("02_clean/sfw"), output_dir=p("02_clean"),
                        sheet=p("03_sheet/character-sheet.png"))
        if step == "sheet":
            return dict(inputs=[p("02_clean/sfw")], out=p("03_sheet/character-sheet.png"),
                        log_dir=p("03_sheet/codex_sheet"), rating=p("02_clean/rating.json"))
        if step == "generate":
            return dict(reference=p("03_sheet/character-sheet.png"), folder=p("04_generate/codex"))
        if step == "fill":
            return dict(fill_existing=p("04_generate/codex/change_outfit"), reference=p("03_sheet/character-sheet.png"))
        if step == "resize":
            return dict(out=resized, groups=[f"{name}={path}" for name, path in groups])
        if step == "build":
            specs = [f"{('collected:nsfw' if name == 'collected_nsfw' else name)}={resized / name}" for name, _ in groups]
            return dict(out=images, groups=specs, nsfw_out=p("05_caption/images_nsfw"),
                        character=f"{meta['character']} ({meta['work']})", trigger=meta["trigger"])
        if step == "sheets":
            self.params()  # Grok uses the project params while authoring the vocabulary.
            return dict(images=images, manifest=images / "manifest.json", out=vocab)
        if step == "check":
            return dict(vocab=vocab / "vocab.json", names=vocab / "names.json",
                        params=self.params, main_outfit=meta["main_outfit_id"] or None)
        if step == "caption":
            return dict(character=meta["character"], work=meta["work"], trigger=meta["trigger"],
                        images=p("05_caption/images_nsfw") if nsfw else images, manifest=images / "manifest.json",
                        vocab=vocab / "vocab.json", main_outfit=vocab / "main_outfit.json", params=self.params,
                        out=captions, final_dir=None if nsfw else p("05_caption/train_set"))
        if step == "convert":
            captions = p("05_caption/captions_nsfw")
            return dict(json_dir=captions / "json", txt_out=captions / "txt", trigger=meta["trigger"], validate_with=captions)
        if step == "train":
            return dict(train_dir=str(p("05_caption/train_set")), trigger=meta["trigger"], work_dir=str(p("06_train")),
                        sd_scripts=str(e / "sd-scripts"), venv=str(e / ".venv"),
                        model=str(e / "models/novaAnimeAM_v6029B.safetensors"),
                        qwen3=str(e / "models/qwen_3_06b_base.safetensors"), vae=str(e / "models/qwen_image_vae_train.safetensors"))
        raise ValueError(f"Unknown workspace step: {step}")


# Only these arguments receive workspace defaults; their legacy defaults are
# restored when --workspace is absent. Explicit values are never replaced.
DEFAULT_FIELDS = {
    "grok_collect": "query out", "grok_clean": "target nsfw sfw codex_clean out collected_sfw collected_nsfw sheet",
    "grok_generate": "reference out", "grok_vocab": "project_dir out images manifest params",
    "grok_caption": "project_dir images out final_dir manifest", "grok_upscale": "out_dir images",
    "collect": "query save_dir", "dedup": "out sources model_dir", "clean": "target input_dir output_dir sheet",
    "sheet": "inputs out log_dir rating",
    "generate": "reference folder", "fill": "fill_existing reference target",
    "resize": "out groups", "build": "out groups character trigger nsfw_out",
    "sheets": "images manifest out", "check": "vocab names params main_outfit",
    "caption": "character work trigger images manifest vocab main_outfit params out final_dir",
    "convert": "json_dir txt_out trigger validate_with",
    "train": "train_dir trigger work_dir sd_scripts venv model qwen3 vae",
}


def parse_args(parser, step, argv=None):
    parser.add_argument("--workspace", type=Path, help="Use project.json and the documented workspace paths as defaults")
    steps = step if isinstance(step, dict) else {step: parser}
    actions = []
    for name, cli in steps.items():
        if cli is not parser:
            cli.add_argument("--workspace", type=Path, default=argparse.SUPPRESS)
        for action in cli._actions:
            if action.dest not in DEFAULT_FIELDS[name].split():
                continue
            actions.append((name, action, action.default, action.required, action.nargs))
            action.default = None
            action.required = False
            if not action.option_strings:
                action.nargs = "*" if action.nargs == "+" else "?"
    a = parser.parse_args(argv)
    if isinstance(step, dict):
        step = a.cmd
    workspace = a.workspace
    del a.workspace
    try:
        ws = Workspace(workspace) if workspace is not None else None
        nsfw = getattr(a, "nsfw_schema", False)
        defaults = ws.defaults(step, nsfw) if ws else {}
        if step == "fill" and ws:
            defaults["target"] = 2 * a.n
        explicit_main = getattr(a, "main_outfit", None)
        for name, action, old_default, required, nargs in actions:
            if name != step:
                continue
            value = getattr(a, action.dest)
            if value is None or (nargs == "+" and value == []):
                default = defaults.get(action.dest, old_default)
                if step == "train" and action.dest == "venv" and a.python:
                    default = old_default
                value = default() if callable(default) else default
                setattr(a, action.dest, value)
                if (required or (not action.option_strings and nargs in (None, "+"))) and value is None:
                    parser.error(f"the following argument is required: {action.option_strings[-1] if action.option_strings else action.dest}")
        if step == "fill" and a.fill_existing is True and ws:
            a.fill_existing = defaults["fill_existing"]
        if step == "fill" and a.fill_existing is True:
            parser.error("--fill-existing requires a folder or --workspace")
        if step == "check" and ws and explicit_main is not None:
            ws.set_main_outfit(explicit_main)
        if step == "caption":
            del a.nsfw_schema
        return a
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


def create(workspace, work, character, trigger, env):
    root = Path(workspace).expanduser().resolve()
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir()  # Fresh WS, matching step 00's mkdir without -p.
    for directory in DIRECTORIES:
        (root / directory).mkdir(parents=True, exist_ok=True)
    project = dict(work=work, character=character, trigger=trigger,
                   env=str(Path(env).expanduser().resolve()), main_outfit_id="")
    (root / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return root


def approve_sheet(workspace):
    sheet = Path(workspace).expanduser().resolve() / "03_sheet/character-sheet.png"
    if not sheet.is_file():
        raise ValueError(f"找不到角色設定圖：{sheet}")
    record = dict(sheet="03_sheet/character-sheet.png", sha256=hashlib.sha256(sheet.read_bytes()).hexdigest(),
                  approved_at=datetime.now().astimezone().isoformat())
    (sheet.parent / "sheet_approved.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", "utf-8")


def check_sheet_approved(sheet_path):
    sheet = Path(sheet_path)
    approval = sheet.parent / "sheet_approved.json"
    message = "請確認角色設定圖後執行 python -B scripts/ws.py approve-sheet --workspace <WS>。"
    if not sheet.is_file():
        raise ValueError(f"找不到角色設定圖：{sheet}；{message}")
    if not approval.is_file():
        raise ValueError(f"角色設定圖尚未核准：{approval}；{message}")
    try:
        record = json.loads(approval.read_text("utf-8"))
    except ValueError:
        raise ValueError(f"角色設定圖核准紀錄無效：{approval}；{message}") from None
    if record.get("sha256") != hashlib.sha256(sheet.read_bytes()).hexdigest():
        raise ValueError(f"角色設定圖與核准雜湊不符：{sheet}；{message}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("create", help="Create a fresh workspace and project.json")
    for field in ("workspace", "work", "character", "trigger", "env"):
        command.add_argument("--" + field, required=True)
    command = sub.add_parser("approve-sheet", help="記錄目前角色設定圖的核准雜湊")
    command.add_argument("--workspace", required=True)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        if command == "approve-sheet":
            approve_sheet(**args)
        else:
            create(**args)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
