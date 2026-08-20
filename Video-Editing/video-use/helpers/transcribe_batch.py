"""Import a directory of Agent-produced ASR Router results into video-use."""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from transcribe import transcribe_one


VIDEO_EXTS = {".mp4", ".MP4", ".mov", ".MOV", ".mkv", ".MKV", ".avi", ".AVI", ".m4v"}


def find_videos(videos_dir: Path) -> list[Path]:
    return sorted(
        path for path in videos_dir.iterdir()
        if path.is_file() and path.suffix in VIDEO_EXTS
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import ASR Router results for every video in a directory"
    )
    parser.add_argument("videos_dir", type=Path)
    parser.add_argument("--edit-dir", type=Path, default=None)
    parser.add_argument(
        "--asr-results-dir",
        type=Path,
        required=True,
        help="Directory containing <video-stem>.json normalized Router results",
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    videos_dir = args.videos_dir.resolve()
    results_dir = args.asr_results_dir.resolve()
    if not videos_dir.is_dir():
        sys.exit(f"not a directory: {videos_dir}")
    if not results_dir.is_dir():
        sys.exit(f"not a directory: {results_dir}")

    edit_dir = (args.edit_dir or (videos_dir / "edit")).resolve()
    videos = find_videos(videos_dir)
    if not videos:
        sys.exit(f"no videos found in {videos_dir}")

    cached = [v for v in videos if (edit_dir / "transcripts" / f"{v.stem}.json").exists()]
    pending = [v for v in videos if v not in cached]
    print(f"found {len(videos)} videos ({len(cached)} cached, {len(pending)} to import)")
    if not pending:
        return

    missing = [results_dir / f"{video.stem}.json" for video in pending
               if not (results_dir / f"{video.stem}.json").is_file()]
    if missing:
        sys.exit("missing Router results:\n" + "\n".join(str(path) for path in missing))

    errors: list[tuple[Path, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                transcribe_one,
                video,
                edit_dir,
                results_dir / f"{video.stem}.json",
                False,
            ): video
            for video in pending
        }
        for future in as_completed(futures):
            video = futures[future]
            try:
                output = future.result()
                print(f"  + {video.stem} -> {output.name}")
            except Exception as exc:
                errors.append((video, str(exc)))
                print(f"  x {video.stem} FAILED: {exc}")

    if errors:
        for video, message in errors:
            print(f"{video.name}: {message}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
