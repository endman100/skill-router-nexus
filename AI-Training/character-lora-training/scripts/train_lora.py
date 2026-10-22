# -*- coding: utf-8 -*-
"""Anima character LoRA training launcher (Linux / Windows, Python stdlib only).

Builds kwargs_train.json + config.toml in --work-dir, then runs
sd-scripts/anima_train_network.py through accelerate in the given venv / python
environment, automatically resuming from the newest saved state.

Layout of --work-dir:
  kwargs_train.json, config.toml       generated training settings
  models/                              <trigger>-0000NN.safetensors, *-state dirs, train.log
  images_regularization_1to1/           regularization subset (only if needed)

Example:
  python train_lora.py --train-dir run/train_set --trigger takane_yasuko --work-dir run/lora_work \
      --sd-scripts repos/sd-scripts --venv repos/.venv \
      --model models/novaAnimeAM_v6029B.safetensors --qwen3 models/qwen_3_06b_base.safetensors \
      --vae models/qwen_image_vae_train.safetensors
"""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import json
import math
import os
import shutil
import subprocess
import sys

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TARGET_TRAIN_SAMPLES = 480


class Tee:
    """Send launcher and piped child output to both the console and the log."""

    def __init__(self, console, log):
        self.console = console
        self.log = log

    def write(self, text):
        self.console.write(text)
        return self.log.write(text)

    def flush(self):
        self.console.flush()
        self.log.flush()


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
    """Write the sd-scripts dataset configuration without a TOML dependency."""
    subsets = [{"image_dir": kw["train_dir"], "class_tokens": class_tokens,
                "num_repeats": kw["num_repeats"], "caption_extension": "txt"}]
    if kw.get("regularization_dir"):
        subsets.append({"image_dir": kw["regularization_dir"], "class_tokens": "regularization",
                        "num_repeats": kw["num_repeats_regularization"], "caption_extension": "txt",
                        "is_reg": True})
    lines = ["[[datasets]]", f"resolution = {kw['resolution']}", f"batch_size = {kw['batch_size']}"]
    for i, s in enumerate(subsets):
        if i:
            lines.append("")
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


def read_state_epoch(state_dir):
    try:
        with open(os.path.join(state_dir, "train_state.json"), encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return None
    epoch = state.get("current_epoch") if isinstance(state, dict) else None
    return epoch if type(epoch) is int else None


def find_last_checkpoint(models, trigger):
    """Choose the highest epoch for this trigger, preferring saved metadata."""
    last_epoch, resume = -1, ""
    prefix, suffix = trigger + "-", "-state"
    for name in os.listdir(models):
        state_dir = os.path.join(models, name)
        if not os.path.isdir(state_dir):
            continue
        numbered_epoch = None
        if name != trigger + suffix:
            if not (name.startswith(prefix) and name.endswith(suffix)):
                continue
            number = name[len(prefix):-len(suffix)]
            if not number.isdigit():
                continue
            numbered_epoch = int(number)
        epoch = read_state_epoch(state_dir)
        if epoch is None:
            epoch = numbered_epoch
        if epoch is not None and epoch > last_epoch:
            last_epoch, resume = epoch, state_dir
    return last_epoch, resume


def build_command(accelerate, sd_scripts, kw, trigger, models, last_epoch, resume):
    """Keep the established Anima argument order; paths are single argv items."""
    cmd = [accelerate, "launch", "--mixed_precision", "bf16", "--num_cpu_threads_per_process", "1",
           os.path.join(sd_scripts, "anima_train_network.py"),
           f"--pretrained_model_name_or_path={kw['pretrained_model_name_or_path']}",
           f"--qwen3={kw['qwen3_path']}", f"--vae={kw['vae_path']}",
           f"--dataset_config={kw['toml_path']}", f"--output_dir={models}", f"--output_name={trigger}",
           "--save_model_as=safetensors", f"--network_module={kw['network_module']}",
           f"--network_dim={kw['network_dim']}", f"--learning_rate={kw['learning_rate']}",
           "--optimizer_type=AdamW8bit", "--lr_scheduler=constant", "--timestep_sampling=sigmoid",
           "--discrete_flow_shift=1.0", f"--max_train_epochs={kw['max_train_epochs']}",
           f"--save_every_n_epochs={kw['save_every_n_epochs']}", "--save_precision", "bf16",
           "--mixed_precision", "bf16", "--gradient_checkpointing", "--cache_latents", "--cache_latents_to_disk"]
    shuffle_caption = True
    dropout = kw["caption_tag_dropout_rate"]
    # Text encoder output caching is incompatible with caption augmentation.
    if not (shuffle_caption or dropout > 0):
        cmd += ["--cache_text_encoder_outputs", "--cache_text_encoder_outputs_to_disk"]
    cmd += ["--vae_chunk_size=64", "--vae_disable_cache", "--persistent_data_loader_workers",
            "--max_data_loader_n_workers", "1", "--network_train_unet_only", "--attn_mode", "sdpa"]
    if shuffle_caption:
        cmd += ["--shuffle_caption", f"--keep_tokens={kw['keep_tokens']}"]
    if dropout > 0:
        cmd.append(f"--caption_tag_dropout_rate={dropout}")
    if kw["enable_bucket"]:
        cmd += ["--enable_bucket", f"--min_bucket_reso={kw['min_bucket_reso']}",
                f"--max_bucket_reso={kw['max_bucket_reso']}"]
    cmd.append("--save_state")
    if resume:
        cmd += [f"--initial_epoch={last_epoch + 1}", "--skip_until_initial_step", f"--resume={resume}"]
    return cmd


def run(args, work):
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
        return 0

    sd_scripts = os.path.abspath(args.sd_scripts)
    for rel in ("anima_train_network.py", os.path.join("networks", "lori_D_anima.py")):
        if not os.path.isfile(os.path.join(sd_scripts, rel)):
            sys.exit(f"missing {os.path.join(sd_scripts, rel)}\n"
                     "Get the required sd-scripts checkout:\n"
                     "  git clone https://github.com/endman100/sd-scripts\n"
                     "  git -C sd-scripts checkout 08d86febb0f9f2fba06517a1983647d02b1337bc\n"
                     "Pass that folder as --sd-scripts.")
    if missing:
        sys.exit(f"model files not found: {missing}")
    if not (args.venv or args.python):
        sys.exit("--venv or --python is required for training")
    _, bin_dir = resolve_python(args)
    env = dict(os.environ)
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    if args.venv:
        env["VIRTUAL_ENV"] = os.path.abspath(args.venv)
    env.update(PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    accelerate = shutil.which("accelerate", path=env["PATH"])
    if not accelerate:
        sys.exit(f"accelerate not found in {bin_dir}")

    models = os.path.join(work, "models")
    for attempt in range(args.max_retries + 1):
        last_epoch, resume = find_last_checkpoint(models, args.trigger)
        if last_epoch >= args.epochs:
            print(f"last epoch {last_epoch} >= final epoch {args.epochs}; no need to train again", flush=True)
            return 0
        if resume:
            print(f"resuming from epoch {last_epoch}: {resume}", flush=True)
        cmd = build_command(accelerate, sd_scripts, kw, args.trigger, models, last_epoch, resume)
        print(f"run_command (attempt {attempt + 1}/{args.max_retries + 1}): {json.dumps(cmd, ensure_ascii=False)}", flush=True)
        with subprocess.Popen(cmd, cwd=sd_scripts, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1) as proc:
            try:
                for line in proc.stdout:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                returncode = proc.wait()
            except KeyboardInterrupt:
                proc.terminate()
                raise
        if returncode == 0:
            print("training finished", flush=True)
            return 0
        print(f"accelerate exited with status {returncode}", flush=True)
        if attempt == args.max_retries:
            print(f"max retries exhausted ({args.max_retries}); stopping", flush=True)
            return returncode if returncode > 0 else 128 - returncode
        print(f"retry {attempt + 1}/{args.max_retries}: re-checking newest state", flush=True)


def main():
    ap = argparse.ArgumentParser(description="Anima character LoRA training (accelerate, auto-resume)")
    ap.add_argument("--train-dir", required=True, help="images + same-name .txt captions")
    ap.add_argument("--trigger", required=True, help="output_name and class_tokens")
    ap.add_argument("--work-dir", required=True, help="config, cache, models/ (checkpoints + train.log)")
    ap.add_argument("--sd-scripts", required=True, help="sd-scripts checkout containing anima_train_network.py")
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
    ap.add_argument("--max-retries", type=int, default=3, help="retries after a failed run (default: 3; 0 disables retries)")
    ap.add_argument("--prepare-only", action="store_true", help="only write kwargs_train.json and config.toml")
    args = ap.parse_args()
    if args.max_retries < 0:
        ap.error("--max-retries must be >= 0")

    work = os.path.abspath(args.work_dir)
    os.makedirs(work, exist_ok=True)
    if args.prepare_only:
        return run(args, work)

    models = os.path.join(work, "models")
    os.makedirs(models, exist_ok=True)
    log_path = os.path.join(models, "train.log")
    # Python open() allows shared reading/writing on Windows, including from children.
    with open(log_path, "a", encoding="utf-8", buffering=1) as log, \
            redirect_stdout(Tee(sys.stdout, log)), redirect_stderr(Tee(sys.stderr, log)):
        print(f"training log: {log_path}", flush=True)
        try:
            return run(args, work)
        except SystemExit as exc:
            if isinstance(exc.code, str):
                print(exc.code, file=sys.stderr, flush=True)
                return 1
            raise
        except OSError as exc:
            print(f"training error: {exc}", file=sys.stderr, flush=True)
            return 1
        except KeyboardInterrupt:
            print("training interrupted", file=sys.stderr, flush=True)
            return 130


if __name__ == "__main__":
    sys.exit(main())
