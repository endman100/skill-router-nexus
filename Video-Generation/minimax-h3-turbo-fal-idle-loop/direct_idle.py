#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

MODEL = "minimax/h3-max/image-to-video"
UPLOAD = "https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3"


def fetch(url, data=None, headers=None, method=None):
    with urlopen(Request(url, data, headers or {}, method=method), timeout=240) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description="One image -> five-second H3 idle loop")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument(
        "--background", choices=("white", "scene"), default="white",
        help="white: flat #ffffff (default), scene: preserve the first frame's background",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    output = args.output or args.input.with_suffix(".idle.mp4")
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(args.input.suffix.lower())
    if not mime:
        parser.error("Input must be PNG or JPEG")
    prompt_path = Path(__file__).resolve().parent / "prompts" / f"{args.background}.txt"
    try:
        prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        parser.error(f"Prompt file not found for --background {args.background}: {prompt_path}")
    body = dict(
        prompt=prompt,
        image_url="https://fal.media/DRY-RUN.png",
        duration=5,
        resolution="768P",
        prompt_expansion_mode="disabled",
        enable_safety_checker=False,
    )
    if args.dry_run:
        print(json.dumps(dict(model=MODEL, body=body, output=str(output)), indent=2))
        return
    key = os.environ.get("FAL_KEY")
    if not key:
        parser.error("FAL_KEY is required unless --dry-run")
    result_file = Path(str(output) + ".result.json")
    if output.exists() or result_file.exists():
        parser.error("Output or result JSON already exists; choose another output")
    image = args.input.read_bytes()
    output.parent.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    lifecycle = json.dumps(dict(expiration_duration_seconds=3600))
    uploaded = json.loads(fetch(
        UPLOAD,
        json.dumps(dict(content_type=mime, file_name=args.input.name)).encode(),
        {**headers, "X-Fal-Object-Lifecycle": lifecycle},
    ))
    fetch(uploaded["upload_url"], image, {"Content-Type": mime}, "PUT")
    body.update(image_url=uploaded["file_url"])
    result = json.loads(fetch(
        f"https://fal.run/{MODEL}",
        json.dumps(body).encode(),
        {**headers, "X-Fal-Store-IO": "0", "X-Fal-No-Retry": "1",
         "X-Fal-Object-Lifecycle-Preference": lifecycle},
    ))
    result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    video = fetch(result["video"]["url"])
    if not video:
        raise ValueError("Downloaded video is empty")
    with output.open("xb") as file:
        file.write(video)
    print(output.resolve())


if __name__ == "__main__":
    main()
