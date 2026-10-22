# -*- coding: utf-8 -*-
"""Anima character LoRA training launcher (Linux / Windows, Python stdlib only).

Builds kwargs_train.json + config.toml in --work-dir, then runs
sd-scripts-wrap/train_with_resume.py (auto-resume from the newest saved state)
with the given venv / python. sd-scripts must be cloned at <sd-scripts-wrap>/sd-scripts.

Layout of --work-dir:
  kwargs_train.json, config.toml       generated training settings
  models/                              <trigger>-0000NN.safetensors, *-state dirs, train.log
  cache_dir/, images_regularization_1to1/ (only with --reg-dir)

Example:
  python train_lora.py --train-dir run/train_set --trigger takane_yasuko --work-dir run/lora_work \
      --sd-scripts-wrap repos/sd-scripts-wrap --venv repos/.venv \
      --model models/novaAnimeAM_v6029B.safetensors --qwen3 models/qwen_3_06b_base.safetensors \
      --vae models/qwen_image_vae_train.safetensors
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TARGET_TRAIN_SAMPLES = 480

# Runs inside the training python (needs `toml`, which sd-scripts installs).
DRIVER = r"""
import importlib.util, json, os, sys
kwargs_path, name, out_dir, wandb_dir, wrap_dir = sys.argv[1:6]
spec = importlib.util.spec_from_file_location("train_with_resume", os.path.join(wrap_dir, "train_with_resume.py"))
twr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(twr)
twr.venv_activate_path = ""  # accelerate is resolved from PATH (set by train_lora.py)
with open(kwargs_path, encoding="utf-8") as f:
    kwargs = json.load(f)
twr.train_with_resume(name, out_dir, wandb_dir, **kwargs)
epoch, state = twr.find_last_checkpoint(out_dir, name, kwargs["save_every_n_epochs"])
print(f"training finished: last epoch {epoch}, state {state}", flush=True)
"""


def list_images(d):
    return sorted(f for f in os.listdir(d) if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS)


def link_or_copy(src, dst):
    if os.path.exists(dst):
        return
    try:
        os.symlink(os.path.abspath(src), dst)
    except OSError:
        shutil.copy2(src, dst)


def make_reg_subset(src_dir, subset_dir, max_images):
    if os.path.exists(subset_dir):
        shutil.rmtree(subset_dir)
    os.makedirs(subset_dir)
    for name in list_images(src_dir)[:max_images]:
        link_or_copy(os.path.join(src_dir, name), os.path.join(subset_dir, name))
        cap = os.path.join(src_dir, os.path.splitext(name)[0] + ".txt")
        if os.path.exists(cap):
            link_or_copy(cap, os.path.join(subset_dir, os.path.basename(cap)))
    return subset_dir


def toml_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return json.dumps(str(v), ensure_ascii=False)  # JSON strings are valid TOML basic strings


def write_config_toml(path, kw, class_tokens):
    """Same structure as sd-scripts-wrap create_toml_file (it rewrites this file when training starts)."""
    subsets = [{"image_dir": kw["train_dir"], "class_tokens": class_tokens,
                "num_repeats": kw["num_repeats"], "caption_extension": "txt"}]
    if kw.get("regularization_dir"):
        subsets.append({"image_dir": kw["regularization_dir"], "class_tokens": "regularization",
                        "num_repeats": kw["num_repeats_regularization"], "caption_extension": "txt",
                        "is_reg": True})
    lines = ["[[datasets]]", f"resolution = {kw['resolution']}", f"batch_size = {kw['batch_size']}"]
    for s in subsets:
        lines.append("[[datasets.subsets]]")
        lines += [f"{k} = {toml_value(v)}" for k, v in s.items()]
    lines += ["", "", "[general]"]
    lines += [f"{k} = {toml_value(kw[k])}" for k in ("enable_bucket", "min_bucket_reso", "max_bucket_reso")]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def resolve_python(args):
    """Return (python executable, directory holding accelerate) for --venv or --python."""
    if args.venv:
        venv = os.path.abspath(args.venv)
        bin_dir = os.path.join(venv, "Scripts" if os.name == "nt" else "bin")
        py = os.path.join(bin_dir, "python.exe" if os.name == "nt" else "python")
    else:
        py = os.path.abspath(args.python) if os.path.exists(args.python) else shutil.which(args.python)
        if not py:
            sys.exit(f"python not found: {args.python}")
        bin_dir = os.path.dirname(py)
        if os.name == "nt" and os.path.isdir(os.path.join(bin_dir, "Scripts")):
            bin_dir = os.path.join(bin_dir, "Scripts")  # base Windows install keeps accelerate.exe in Scripts
    if not os.path.exists(py):
        sys.exit(f"python not found: {py}")
    return py, bin_dir


def build_kwargs(args, work):
    train_dir = os.path.abspath(args.train_dir)
    if not os.path.isdir(train_dir):
        sys.exit(f"--train-dir not found: {train_dir}")
    images = list_images(train_dir)
    if not images:
        sys.exit(f"no images in {train_dir}")
    missing = [f for f in images if not os.path.exists(os.path.join(train_dir, os.path.splitext(f)[0] + ".txt"))]
    if missing:
        sys.exit(f"missing captions ({len(missing)}): {missing[:5]}")
    num_data = len(images)
    num_repeats = max(1, math.ceil(TARGET_TRAIN_SAMPLES / num_data))
    print(f"train images {num_data}, num_repeats {num_repeats} ({num_data * num_repeats} samples/epoch)", flush=True)

    reg_dir, reg_repeats = None, 1
    if args.reg_dir:
        reg_dir = os.path.abspath(args.reg_dir)
        if not os.path.isdir(reg_dir):
            sys.exit(f"--reg-dir not found: {reg_dir}")
        target = num_data * num_repeats
        num_reg = len(list_images(reg_dir))
        if num_reg == 0:
            sys.exit(f"no images in {reg_dir}")
        if num_reg > target:  # keep train:reg = 1:1
            reg_dir = make_reg_subset(reg_dir, os.path.join(work, "images_regularization_1to1"), target)
            num_reg = target
        reg_repeats = max(1, math.ceil(target / num_reg))
        print(f"train/reg samples {target} : {num_reg * reg_repeats}", flush=True)
    else:
        print("no regularization images", flush=True)

    kw = {
        "resolution": args.resolution,
        "batch_size": args.batch,
        "train_dir": train_dir,
        "num_repeats": num_repeats,
    }
    if reg_dir:
        kw["regularization_dir"] = reg_dir
        kw["num_repeats_regularization"] = reg_repeats
    kw.update({
        "toml_path": os.path.join(work, "config.toml"),
        "max_train_epochs": args.epochs,
        "save_every_n_epochs": args.save_every,
        "learning_rate": args.lr,
        "network_dim": args.dim,
        "network_module": "networks.lori_D_anima",
        "train_method": "get_command_anima",
        "cache_dir": os.path.join(work, "cache_dir"),
        "cache_dir_regularization": os.path.join(work, "cache_dir_regularization"),
        "keep_tokens": args.keep_tokens,
        "caption_tag_dropout_rate": args.tag_dropout,
        "enable_bucket": True,
        "min_bucket_reso": args.min_bucket,
        "max_bucket_reso": args.max_bucket,
        "pretrained_model_name_or_path": os.path.abspath(args.model),
        "qwen3_path": os.path.abspath(args.qwen3),
        "vae_path": os.path.abspath(args.vae),
    })
    return kw


def main():
    ap = argparse.ArgumentParser(description="Anima character LoRA training (sd-scripts-wrap auto-resume)")
    ap.add_argument("--train-dir", required=True, help="images + same-name .txt captions")
    ap.add_argument("--trigger", required=True, help="output_name and class_tokens")
    ap.add_argument("--work-dir", required=True, help="config, cache, models/ (checkpoints + train.log)")
    ap.add_argument("--sd-scripts-wrap", required=True, help="sd-scripts-wrap checkout (sd-scripts inside it)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--venv", help="venv dir (has accelerate + sd-scripts requirements)")
    g.add_argument("--python", help="python executable of the training env (alternative to --venv)")
    ap.add_argument("--model", required=True, help="Anima DiT checkpoint .safetensors")
    ap.add_argument("--qwen3", required=True, help="qwen_3_06b_base.safetensors")
    ap.add_argument("--vae", required=True, help="qwen_image_vae_train.safetensors")
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--max-bucket", type=int, default=1280)
    ap.add_argument("--min-bucket", type=int, default=512)
    ap.add_argument("--resolution", type=int, default=1024)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--save-every", type=int, default=5)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--dim", type=int, default=32)
    ap.add_argument("--keep-tokens", type=int, default=2)
    ap.add_argument("--tag-dropout", type=float, default=0.2)
    ap.add_argument("--reg-dir", help="regularization images (default: none)")
    ap.add_argument("--prepare-only", action="store_true", help="only write kwargs_train.json and config.toml")
    args = ap.parse_args()

    work = os.path.abspath(args.work_dir)
    os.makedirs(work, exist_ok=True)
    kw = build_kwargs(args, work)
    kwargs_path = os.path.join(work, "kwargs_train.json")
    with open(kwargs_path, "w", encoding="utf-8") as f:
        json.dump(kw, f, ensure_ascii=False, indent=4)
    write_config_toml(kw["toml_path"], kw, args.trigger)
    print(f"wrote {kwargs_path}\nwrote {kw['toml_path']}", flush=True)

    missing = [p for p in (kw["pretrained_model_name_or_path"], kw["qwen3_path"], kw["vae_path"]) if not os.path.exists(p)]
    if args.prepare_only:
        for p in missing:
            print(f"WARNING: not found: {p}")
        return
    if missing:
        sys.exit(f"model files not found: {missing}")

    wrap = os.path.abspath(args.sd_scripts_wrap)
    for rel in ("train_with_resume.py", os.path.join("sd-scripts", "anima_train_network.py"),
                os.path.join("sd-scripts", "networks", "lori_D_anima.py")):
        if not os.path.exists(os.path.join(wrap, rel)):
            sys.exit(f"missing {os.path.join(wrap, rel)} (clone sd-scripts into <sd-scripts-wrap>/sd-scripts)")
    if not (args.venv or args.python):
        sys.exit("--venv or --python is required for training")
    py, bin_dir = resolve_python(args)
    env = dict(os.environ)
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    if args.venv:
        env["VIRTUAL_ENV"] = os.path.abspath(args.venv)
    env.update(PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    if not shutil.which("accelerate", path=env["PATH"]):
        sys.exit(f"accelerate not found in {bin_dir}")

    models = os.path.join(work, "models")
    os.makedirs(models, exist_ok=True)
    log_path = os.path.join(models, "train.log")
    cmd = [py, "-u", "-c", DRIVER, kwargs_path, args.trigger, models, os.path.join(work, "wandb"), wrap]
    print(f"training log: {log_path}", flush=True)
    with open(log_path, "a", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, cwd=os.path.join(wrap, "sd-scripts"), env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
        try:
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                log.write(line)
                log.flush()
        except KeyboardInterrupt:
            proc.terminate()
            raise
        sys.exit(proc.wait())


if __name__ == "__main__":
    main()
