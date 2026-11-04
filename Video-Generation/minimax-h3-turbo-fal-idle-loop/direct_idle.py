#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

MODEL = "minimax/h3-max/image-to-video"
UPLOAD = "https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3"
PROMPT = """How the reference pictures align with the target video: Picture 1 is the first frame at 0.00 seconds; Picture 2 is the identical final frame at 5.00 seconds.

integrated_multimodal_description: [Shot 1] Create a seamless five-second idle loop in 9:16 between the identical supplied first and end frames. Keep identity, outfit, pose silhouette, and every visible detail exactly as supplied; do not invent character-specific traits. Background must stay flat pure white #ffffff with no gradient, shadow spill, props, or environment change. Camera and framing stay completely locked. Add clearly readable idle life: steady breathing that moves the torso, natural blink cadence, soft hair sway if hair is present, and a slight weight shift. Also add generic soft-body secondary bounce on the chest/bust area that follows the breathing cycle with gentle inertia (visible but not exaggerated; no grabbing, no clothing removal, no erotic staging). Keep hands/arms/legs in the same pose; no speech, mouth acting, head turn, new gesture, pose rewrite, cut, fade, zoom, or camera move. During the final second, ease all motion back to the exact supplied end frame at 5.00 seconds for a clean loop. No captions, subtitles, logos, interface, or visible text.

overall_soundscape: N/A

non_diegetic_music: N/A
"""


def fetch(url, data=None, headers=None, method=None):
    with urlopen(Request(url, data, headers or {}, method=method), timeout=240) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description="One image -> five-second H3 idle loop")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    output = args.output or args.input.with_suffix(".idle.mp4")
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(args.input.suffix.lower())
    if not mime:
        parser.error("Input must be PNG or JPEG")
    image = args.input.read_bytes()
    body = dict(prompt=PROMPT, image_url="https://fal.media/DRY-RUN.png",
                end_image_url="https://fal.media/DRY-RUN.png", duration=5, resolution="768P",
                prompt_expansion_mode="disabled", enable_safety_checker=False)
    if args.dry_run:
        print(json.dumps(dict(model=MODEL, body=body, output=str(output)), indent=2))
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
    body.update(image_url=uploaded["file_url"], end_image_url=uploaded["file_url"])
    result = json.loads(fetch(f"https://fal.run/{MODEL}", json.dumps(body).encode(),
        {**headers, "X-Fal-Store-IO": "0", "X-Fal-No-Retry": "1",
         "X-Fal-Object-Lifecycle-Preference": lifecycle}))
    result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    video = fetch(result["video"]["url"])
    if not video:
        raise ValueError("Downloaded video is empty")
    with output.open("xb") as file:
        file.write(video)
    print(output.resolve())


if __name__ == "__main__":
    main()
