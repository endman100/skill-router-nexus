#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

MODEL = "minimax/h3-max/image-to-video"
UPLOAD = "https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3"
PROMPT = """How the reference pictures align with the target video: Picture 1 is the first frame at 0.00 seconds.

integrated_multimodal_description: [Shot 1] Create a seamless five-second looping idle in 9:16 starting from the supplied first frame. Keep identity, outfit, pose silhouette, and every visible detail exactly as supplied; do not invent character-specific traits. Background must stay flat pure white #ffffff with no gradient, shadow spill, props, or environment change. Camera and framing stay completely locked. Keep continuous full-body idle energy for the entire clip with no freeze, hold, settle, or ease-to-stillness at any time including the final second: steady breathing that moves chest and torso; natural blink cadence; soft hair sway if hair is present; gentle soft-body secondary bounce on the chest/bust following the breath with light inertia; continuous lower-body micro-motion—small left-right hip sway / weight shift in the pelvis, subtle knee give, and tiny ankle or stance rock so legs and hips stay alive with the torso. Prefer periodic cyclic motion whose phase at the end is close to the start so a loop stitches cleanly. Keep overall pose and hand/arm placement; no walking steps, no speech, mouth acting, head turn, new gesture, pose rewrite, clothing removal, grabbing, cut, fade, zoom, or camera move. No captions, subtitles, logos, interface, or visible text.

overall_soundscape: N/A

non_diegetic_music: N/A
"""


def fetch(url, data=None, headers=None, method=None):
    with urlopen(Request(url, data, headers or {}, method=method), timeout=240) as response:
        return response.read()


def seamless_loop(src: Path, dst: Path, cross=0.5):
    """Crossfade end into start so playback loops without a settle-to-still join."""
    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(src)],
        text=True).strip()
    duration = float(probe)
    if duration <= cross * 2:
        raise ValueError(f"video too short for {cross}s crossfade: {duration}")
    offset = duration - cross
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Dual-input xfade keeps constant frame rate; single-split path can yield 1/0 fps.
    subprocess.check_call([
        "ffmpeg", "-y", "-i", str(src), "-i", str(src),
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration={cross}:offset={offset}",
        "-an", "-t", f"{duration}", "-c:v", "libx264", "-b:v", "5M", "-maxrate", "6M", "-bufsize", "10M", "-preset", "slow", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(dst),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description="One image -> five-second H3 idle loop")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-raw", action="store_true",
                        help="also keep pre-crossfade provider mp4 as OUTPUT.raw.mp4")
    parser.add_argument("--no-loop-xfade", action="store_true",
                        help="skip ffmpeg end/start crossfade")
    parser.add_argument("--cross", type=float, default=0.15,
                        help="seamless loop crossfade seconds (default 0.15; 0.5 often flickers)")
    args = parser.parse_args()
    output = args.output or args.input.with_suffix(".idle.mp4")
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(args.input.suffix.lower())
    if not mime:
        parser.error("Input must be PNG or JPEG")
    image = args.input.read_bytes()
    # Intentionally omit end_image_url: forcing the still as last frame makes H3 ease-to-still.
    body = dict(prompt=PROMPT, image_url="https://fal.media/DRY-RUN.png",
                duration=5, resolution="768P",
                prompt_expansion_mode="disabled", enable_safety_checker=False)
    if args.dry_run:
        print(json.dumps(dict(model=MODEL, body=body, output=str(output),
                              loop_xfade=(not args.no_loop_xfade), cross=args.cross), indent=2))
        return
    key = os.environ.get("FAL_KEY")
    if not key:
        parser.error("FAL_KEY is required unless --dry-run")
    result_file = Path(str(output) + ".result.json")
    if output.exists() or result_file.exists():
        parser.error("Output or result JSON already exists; choose another output")
    output.parent.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    lifecycle = json.dumps(dict(expiration_duration_seconds=3600))
    uploaded = json.loads(fetch(UPLOAD,
        json.dumps(dict(content_type=mime, file_name=args.input.name)).encode(),
        {**headers, "X-Fal-Object-Lifecycle": lifecycle}))
    fetch(uploaded["upload_url"], image, {"Content-Type": mime}, "PUT")
    body.update(image_url=uploaded["file_url"])
    result = json.loads(fetch(f"https://fal.run/{MODEL}", json.dumps(body).encode(),
        {**headers, "X-Fal-Store-IO": "0", "X-Fal-No-Retry": "1",
         "X-Fal-Object-Lifecycle-Preference": lifecycle}))
    result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    video = fetch(result["video"]["url"])
    if not video:
        raise ValueError("Downloaded video is empty")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video)
        raw = Path(tmp.name)
    try:
        if args.no_loop_xfade:
            with output.open("xb") as file:
                file.write(raw.read_bytes())
        else:
            seamless_loop(raw, output, cross=args.cross)
            if args.keep_raw:
                raw_out = Path(str(output) + ".raw.mp4")
                raw_out.write_bytes(raw.read_bytes())
    finally:
        raw.unlink(missing_ok=True)
    print(output.resolve())


if __name__ == "__main__":
    main()
