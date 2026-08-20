from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


@dataclass(frozen=True)
class LyricEvent:
    absolute_start: float
    absolute_end: float
    text: str
    clip_start: float

    @property
    def relative_start(self) -> float:
        return self.absolute_start - self.clip_start

    @property
    def relative_end(self) -> float:
        return self.absolute_end - self.clip_start


@dataclass(frozen=True)
class SongJob:
    interval_no: int
    title: str
    clip_start: float
    clip_end: float
    lyrics: tuple[LyricEvent, ...]

    @property
    def duration(self) -> float:
        return self.clip_end - self.clip_start


@dataclass(frozen=True)
class CameraKey:
    time_seconds: float
    offset_x: float
    offset_y: float
    section: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def to_traditional(text: str) -> str:
    try:
        from opencc import OpenCC
    except ImportError as error:
        raise RuntimeError(
            "Traditional Chinese output requires opencc-python-reimplemented"
        ) from error
    converter = getattr(to_traditional, "_converter", None)
    if converter is None:
        converter = OpenCC("s2t")
        setattr(to_traditional, "_converter", converter)
    return str(converter.convert(text))


def clean_caption_text(text: str, *, convert_chinese: bool = True) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return to_traditional(normalized) if convert_chinese else normalized


def parse_source_labels(row: dict[str, str]) -> set[str]:
    labels = {row.get("song_label", "").strip()}
    labels.update(
        value.strip()
        for value in re.split(r"[;|]", row.get("source_song_labels", ""))
        if value.strip()
    )
    labels.discard("")
    labels.discard("talk")
    return labels


def adjusted_events(events: list[LyricEvent], clip_end: float) -> list[LyricEvent]:
    adjusted: list[LyricEvent] = []
    for index, event in enumerate(events):
        next_start = (
            events[index + 1].absolute_start if index + 1 < len(events) else clip_end
        )
        end = event.absolute_end
        if end <= event.absolute_start:
            end = min(next_start - 0.08, event.absolute_start + 1.2)
        end = min(end, next_start - 0.04, clip_end)
        if end <= event.absolute_start:
            end = min(clip_end, event.absolute_start + 0.25)
        adjusted.append(
            LyricEvent(event.absolute_start, end, event.text, event.clip_start)
        )
    return adjusted


def join_caption_text(left: str, right: str) -> str:
    if not left or not right:
        return left + right
    if left[-1].isascii() and right[0].isascii():
        return f"{left} {right}"
    return left + right


def coalesce_short_events(events: list[LyricEvent]) -> list[LyricEvent]:
    merged: list[LyricEvent] = []
    for event in events:
        if not merged:
            merged.append(event)
            continue
        previous = merged[-1]
        gap = event.absolute_start - previous.absolute_end
        short_fragment = len(previous.text) <= 3 or len(event.text) <= 3
        combined_length = len(previous.text) + len(event.text)
        if short_fragment and gap <= 0.9 and combined_length <= 32:
            merged[-1] = LyricEvent(
                previous.absolute_start,
                max(previous.absolute_end, event.absolute_end),
                join_caption_text(previous.text, event.text),
                previous.clip_start,
            )
        else:
            merged.append(event)
    return merged


def phrase_events_for_interval(
    interval: dict[str, str], phrases: list[dict[str, str]]
) -> tuple[LyricEvent, ...]:
    clip_start = float(interval["cut_start_seconds"])
    clip_end = float(interval["cut_end_seconds"])
    lyric_start = float(interval.get("start_seconds") or clip_start)
    lyric_end = float(interval.get("end_seconds") or clip_end)
    accepted_labels = parse_source_labels(interval)
    events: list[LyricEvent] = []
    for phrase in phrases:
        start = float(phrase["start_seconds"])
        end = float(phrase["end_seconds"])
        if phrase.get("song_label", "").strip() not in accepted_labels:
            continue
        if start < lyric_start - 0.2 or start > lyric_end + 0.2:
            continue
        language = phrase.get("language_guess", phrase.get("language", "")).lower()
        convert_chinese = language not in {"ja", "japanese", "en", "english"}
        raw_text = phrase.get("repaired_text") or phrase.get("text") or ""
        text = clean_caption_text(raw_text, convert_chinese=convert_chinese)
        if text:
            events.append(LyricEvent(start, end, text, clip_start))
    events.sort(key=lambda item: (item.absolute_start, item.absolute_end))
    return tuple(coalesce_short_events(adjusted_events(events, clip_end)))


def load_jobs(
    intervals_path: Path, phrases_path: Path, selected: set[int] | None = None
) -> list[SongJob]:
    intervals = read_csv(intervals_path)
    phrases = read_csv(phrases_path)
    jobs: list[SongJob] = []
    for interval in intervals:
        interval_no = int(interval["interval_no"])
        if selected and interval_no not in selected:
            continue
        clip_start = float(interval["cut_start_seconds"])
        clip_end = float(interval["cut_end_seconds"])
        if clip_end <= clip_start:
            raise ValueError(f"Interval {interval_no} has a non-positive duration")
        lyrics = phrase_events_for_interval(interval, phrases)
        if not lyrics:
            raise ValueError(f"Interval {interval_no} has no matching lyric phrases")
        jobs.append(
            SongJob(
                interval_no=interval_no,
                title=to_traditional(interval["song_label"].strip()),
                clip_start=clip_start,
                clip_end=clip_end,
                lyrics=lyrics,
            )
        )
    found = {job.interval_no for job in jobs}
    if selected and found != selected:
        raise ValueError(f"Requested intervals not found: {sorted(selected - found)}")
    return jobs


def display_width(text: str) -> int:
    return sum(
        2 if unicodedata.east_asian_width(character) in "WFA" else 1
        for character in text
    )


def split_caption_line(text: str, max_columns: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for character in text:
        if current and display_width(current + character) > max_columns:
            lines.append(current.rstrip())
            current = ""
        current += character
    if current:
        lines.append(current.rstrip())
    return lines


def wrap_subtitle_text(text: str, max_columns: int = 28) -> str:
    if display_width(text) <= max_columns:
        return text
    lines = split_caption_line(text, max_columns)
    if len(lines) <= 2:
        return r"\N".join(lines)
    midpoint = math.ceil(display_width(text) / 2)
    left = ""
    for character in text:
        if left and display_width(left + character) > midpoint:
            break
        left += character
    return left.rstrip() + r"\N" + text[len(left) :].lstrip()


def ass_escape(text: str) -> str:
    return wrap_subtitle_text(text).replace("{", r"\{").replace("}", r"\}")


def ass_time(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100.0)))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{fraction:02d}"


def safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    cleaned = re.sub(r"\s+", "_", cleaned).strip(" ._")
    return cleaned or "untitled"


def build_camera_keys(job: SongJob) -> tuple[CameraKey, ...]:
    first_lyric = max(0.0, job.lyrics[0].relative_start)
    last_lyric = min(job.duration, job.lyrics[-1].relative_end)
    candidates: list[tuple[float, str]] = [(0.0, "intro")]
    if first_lyric >= 8.0:
        candidates.append((first_lyric, "first_lyric"))
    for left, right in zip(job.lyrics, job.lyrics[1:]):
        gap = right.relative_start - left.relative_end
        if gap >= 12.0:
            candidates.append(
                ((left.relative_end + right.relative_start) / 2.0, "instrumental")
            )
    cursor = 60.0
    while cursor < job.duration - 20.0:
        candidates.append((cursor, "section"))
        cursor += 60.0
    if job.duration - last_lyric >= 8.0:
        candidates.append((last_lyric, "tail"))
    candidates.append((job.duration, "end"))
    candidates.sort()
    deduplicated: list[tuple[float, str]] = []
    for candidate in candidates:
        if not deduplicated or candidate[0] - deduplicated[-1][0] >= 7.0:
            deduplicated.append(candidate)
        elif candidate[0] == job.duration:
            deduplicated[-1] = candidate
    x_pattern = (0.0, -18.0, 14.0, -11.0, 18.0, -7.0, 12.0)
    y_pattern = (0.0, 6.0, -5.0, 7.0, -6.0, 4.0, -3.0)
    keys = [
        CameraKey(
            time_value,
            x_pattern[index % len(x_pattern)],
            y_pattern[index % len(y_pattern)],
            section,
        )
        for index, (time_value, section) in enumerate(deduplicated)
    ]
    keys[0] = CameraKey(0.0, 0.0, 0.0, keys[0].section)
    keys[-1] = CameraKey(job.duration, 0.0, 0.0, "end")
    return tuple(keys)


def smootherstep(value: float) -> float:
    bounded = min(1.0, max(0.0, value))
    return bounded**3 * (bounded * (bounded * 6.0 - 15.0) + 10.0)


def camera_offset(
    time_seconds: float, keys: tuple[CameraKey, ...]
) -> tuple[float, float]:
    left, right = keys[0], keys[-1]
    for candidate_left, candidate_right in zip(keys, keys[1:]):
        if candidate_left.time_seconds <= time_seconds <= candidate_right.time_seconds:
            left, right = candidate_left, candidate_right
            break
    span = max(0.001, right.time_seconds - left.time_seconds)
    progress = smootherstep((time_seconds - left.time_seconds) / span)
    x = left.offset_x + (right.offset_x - left.offset_x) * progress
    y = left.offset_y + (right.offset_y - left.offset_y) * progress
    x += 10.0 * math.sin(math.tau * time_seconds / 17.0 + 0.35)
    x += 4.0 * math.sin(math.tau * time_seconds / 43.0 + 1.40)
    y += 4.0 * math.sin(math.tau * time_seconds / 23.0 + 0.80)
    y += 1.5 * math.sin(math.tau * time_seconds / 53.0 + 2.10)
    return x, y


def camera_section(time_seconds: float, keys: tuple[CameraKey, ...]) -> str:
    for left, right in zip(keys, keys[1:]):
        if left.time_seconds <= time_seconds < right.time_seconds:
            return left.section
    return keys[-1].section


def ffmpeg_filter_path(path: Path) -> str:
    return path.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")


def smootherstep_expression(progress: str) -> str:
    return f"({progress})^3*((({progress})*6-15)*({progress})+10)"


def camera_key_expression(keys: tuple[CameraKey, ...], axis: str) -> str:
    attribute = "offset_x" if axis == "x" else "offset_y"
    tail = f"{getattr(keys[-1], attribute):.6f}"
    for left, right in reversed(list(zip(keys, keys[1:]))):
        span = right.time_seconds - left.time_seconds
        progress = f"((t-{left.time_seconds:.6f})/{span:.6f})"
        eased = smootherstep_expression(progress)
        start_value = getattr(left, attribute)
        delta = getattr(right, attribute) - start_value
        value = f"({start_value:.6f}+({delta:.6f})*({eased}))"
        tail = f"if(lt(t,{right.time_seconds:.6f}),{value},{tail})"
    return tail


def build_filter_graph(
    *,
    job: SongJob,
    camera_keys: tuple[CameraKey, ...],
    base_x: float,
    base_y: float,
    crop_width: int,
    crop_height: int,
    subtitle_path: Path,
    fonts_dir: Path,
    mask_ui: bool = True,
) -> str:
    key_x = camera_key_expression(camera_keys, "x")
    key_y = camera_key_expression(camera_keys, "y")
    center_x = f"({base_x:.6f}+({key_x})+10*sin(2*PI*t/17+0.35)+4*sin(2*PI*t/43+1.40))"
    center_y = f"({base_y:.6f}+({key_y})+4*sin(2*PI*t/23+0.80)+1.5*sin(2*PI*t/53+2.10))"
    left = f"(({center_x})-{crop_width / 2.0:.6f})"
    top = f"(({center_y})-{crop_height / 2.0:.6f})"
    video = (
        f"[0:v]trim=duration={job.duration:.6f},setpts=PTS-STARTPTS,"
        "format=yuv420p,hwupload,libplacebo=w=1920:h=1080:"
        f"crop_w={crop_width}:crop_h={crop_height}:crop_x='{left}':crop_y='{top}':"
        "upscaler=ewa_lanczos:downscaler=ewa_lanczos,hwdownload,format=yuv420p"
    )
    if mask_ui:
        video += (
            ",drawbox=x=0:y=0:w=iw:h=68:color=0x050A0F@1.00:t=fill"
            ",drawbox=x=0:y=918:w=iw:h=162:color=0x050A0F@1.00:t=fill"
        )
    video += (
        f",ass=filename='{ffmpeg_filter_path(subtitle_path)}'"
        f":fontsdir='{ffmpeg_filter_path(fonts_dir)}'[v]"
    )
    audio = f"[1:a]atrim=duration={job.duration:.6f},asetpts=PTS-STARTPTS[a]"
    return f"{video};{audio}"


def probe_video(path: Path) -> dict[str, object]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(result.stdout)
    stream = payload["streams"][0]
    numerator, denominator = (
        int(value) for value in stream["avg_frame_rate"].split("/")
    )
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": numerator / denominator,
        "duration": float(payload["format"]["duration"]),
    }


def can_reuse_output(path: Path, expected_duration: float) -> bool:
    if not path.exists():
        return False
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout)
        duration = float(payload["format"]["duration"])
        stream_types = {stream["codec_type"] for stream in payload["streams"]}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return (
        stream_types >= {"video", "audio"} and abs(duration - expected_duration) <= 0.08
    )


def prepare_fonts(output_dir: Path) -> Path:
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    fonts_dir = output_dir / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        (
            Path(r"C:\Windows\Fonts\NotoSerifTC-VF.ttf"),
            fonts_dir / "NotoSerifTC-Medium.ttf",
            500.0,
        ),
        (
            Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf"),
            fonts_dir / "NotoSansTC-Regular.ttf",
            400.0,
        ),
    ]
    for source, destination, weight in specs:
        if destination.exists():
            continue
        if not source.exists():
            raise FileNotFoundError(f"Required font is missing: {source}")
        font = TTFont(source)
        instantiateVariableFont(
            font, {"wght": weight}, inplace=False, updateFontNames=True
        ).save(destination)
    return fonts_dir


def subtitle_header(job: SongJob) -> str:
    return f"""[Script Info]
Title: {job.title} MV-Lite
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Lyrics,Noto Serif TC,54,&H00F8F7F2,&H00F8F7F2,&H8808121C,&H66040B12,0,0,0,0,100,100,0,0,1,3.2,0.8,2,120,120,102,1
Style: Title,Noto Serif TC,88,&H00FAFAF7,&H00FAFAF7,&H8008121C,&H60040B12,-1,0,0,0,100,100,0,0,1,2.4,0.5,7,110,110,110,1
Style: Credit,Noto Sans TC,29,&H00DCEEF0,&H00DCEEF0,&H9008121C,&H60040B12,0,0,0,0,100,100,0,0,1,1.8,0.3,7,116,116,110,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""


def write_subtitles(
    job: SongJob, output_dir: Path, credit: str
) -> tuple[Path, Path, Path]:
    stem = f"{job.interval_no:02d}_{safe_filename(job.title)}"
    ass_path = output_dir / f"{stem}.ass"
    timeline_path = output_dir / f"{stem}_lyric_timeline.csv"
    lyric_rows = [
        {
            "event": index,
            "absolute_start": f"{event.absolute_start:.3f}",
            "absolute_end": f"{event.absolute_end:.3f}",
            "relative_start": f"{event.relative_start:.3f}",
            "relative_end": f"{event.relative_end:.3f}",
            "text": event.text,
            "source": "existing repaired Qwen3 phrase label",
        }
        for index, event in enumerate(job.lyrics, start=1)
    ]
    write_csv(timeline_path, lyric_rows)
    title_end = max(3.0, min(9.5, job.lyrics[0].relative_start - 0.6))
    tail_start = max(job.lyrics[-1].relative_end + 0.8, job.duration - 10.8)
    events = [
        f"Dialogue: 2,0:00:00.55,{ass_time(title_end)},Title,,0,0,0,,{{\\fad(500,750)\\pos(110,760)}}{ass_escape(job.title)}",
        f"Dialogue: 2,0:00:01.10,{ass_time(title_end + 0.6)},Credit,,0,0,0,,{{\\fad(650,750)\\pos(116,862)}}{ass_escape(credit)}",
        f"Dialogue: 2,{ass_time(tail_start)},{ass_time(max(tail_start + 0.5, job.duration - 0.7))},Credit,,0,0,0,,{{\\fad(500,700)\\pos(116,862)}}{ass_escape(job.title)}",
    ]
    events.extend(
        "Dialogue: 1,"
        f"{ass_time(event.relative_start)},{ass_time(event.relative_end)},Lyrics,,0,0,0,,"
        f"{{\\fad(100,100)}}{ass_escape(event.text)}"
        for event in job.lyrics
    )
    ass_path.write_text(
        subtitle_header(job) + "\n".join(events) + "\n", encoding="utf-8-sig"
    )
    return ass_path, timeline_path, prepare_fonts(output_dir)


def detect_character(
    source_video: Path,
    model_path: Path,
    job: SongJob,
    fps: float,
    sample_seconds: float,
    confidence: float,
    device: str,
) -> list[dict[str, object]]:
    from ultralytics import YOLO

    model = YOLO(str(model_path))
    capture = cv2.VideoCapture(str(source_video))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open source video: {source_video}")
    sample_times = np.arange(0.0, job.duration, sample_seconds).tolist()
    sample_times.append(max(0.0, job.duration - 1.0 / fps))
    rows: list[dict[str, object]] = []
    frames: list[np.ndarray] = []
    times: list[float] = []
    try:
        for relative_time in sample_times:
            capture.set(
                cv2.CAP_PROP_POS_FRAMES,
                int(round((job.clip_start + relative_time) * fps)),
            )
            ok, frame = capture.read()
            if not ok:
                continue
            frames.append(frame)
            times.append(float(relative_time))
            if len(frames) >= 16:
                rows.extend(
                    predict_people(model, frames, times, job, confidence, device)
                )
                frames.clear()
                times.clear()
        if frames:
            rows.extend(predict_people(model, frames, times, job, confidence, device))
    finally:
        capture.release()
    if not rows:
        raise RuntimeError(
            f"Character detector produced no samples for interval {job.interval_no}"
        )
    return rows


def predict_people(
    model: object,
    frames: list[np.ndarray],
    times: list[float],
    job: SongJob,
    confidence: float,
    device: str,
) -> list[dict[str, object]]:
    results = model.predict(frames, conf=confidence, verbose=False, device=device)
    rows: list[dict[str, object]] = []
    for relative_time, result in zip(times, results):
        people = [box for box in result.boxes if int(box.cls.item()) == 0]
        row: dict[str, object] = {
            "relative_seconds": f"{relative_time:.3f}",
            "absolute_seconds": f"{job.clip_start + relative_time:.3f}",
            "detected": False,
            "confidence": "0.000000",
            "x1": "",
            "y1": "",
            "x2": "",
            "y2": "",
            "center_x": "",
            "center_y": "",
        }
        if people:
            box = max(people, key=lambda item: float(item.conf.item()))
            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0])
            row.update(
                {
                    "detected": True,
                    "confidence": f"{float(box.conf.item()):.6f}",
                    "x1": f"{x1:.3f}",
                    "y1": f"{y1:.3f}",
                    "x2": f"{x2:.3f}",
                    "y2": f"{y2:.3f}",
                    "center_x": f"{(x1 + x2) / 2.0:.3f}",
                    "center_y": f"{(y1 + y2) / 2.0:.3f}",
                }
            )
        rows.append(row)
    return rows


def detection_summary(
    rows: list[dict[str, object]],
    keys: tuple[CameraKey, ...],
    source_width: int,
    source_height: int,
    crop_width: int,
    crop_height: int,
) -> dict[str, object]:
    detected = [row for row in rows if bool(row["detected"])]
    median_x = (
        float(np.median([float(row["center_x"]) for row in detected]))
        if detected
        else source_width / 2
    )
    median_y = (
        float(np.median([float(row["center_y"]) for row in detected]))
        if detected
        else source_height / 2
    )
    offsets = np.asarray(
        [
            camera_offset(float(t), keys)
            for t in np.linspace(0, keys[-1].time_seconds, 4000)
        ]
    )
    base_x = float(
        np.clip(
            median_x,
            crop_width / 2 - offsets[:, 0].min(),
            source_width - crop_width / 2 - offsets[:, 0].max(),
        )
    )
    base_y = float(
        np.clip(
            median_y,
            crop_height / 2 - offsets[:, 1].min(),
            source_height - crop_height / 2 - offsets[:, 1].max(),
        )
    )
    safe = sum(
        box_inside_crop(row, base_x, base_y, crop_width, crop_height, keys)
        for row in detected
    )
    return {
        "samples": len(rows),
        "detected_samples": len(detected),
        "detection_rate": len(detected) / len(rows),
        "mean_confidence": float(
            np.mean([float(row["confidence"]) for row in detected])
        )
        if detected
        else 0.0,
        "median_center": [median_x, median_y],
        "camera_base_center": [base_x, base_y],
        "safe_box_rate": safe / len(detected) if detected else 0.0,
    }


def box_inside_crop(
    row: dict[str, object],
    base_x: float,
    base_y: float,
    crop_width: int,
    crop_height: int,
    keys: tuple[CameraKey, ...],
) -> bool:
    offset_x, offset_y = camera_offset(float(row["relative_seconds"]), keys)
    left = base_x + offset_x - crop_width / 2
    top = base_y + offset_y - crop_height / 2
    margin = 8.0
    return (
        float(row["x1"]) >= left + margin
        and float(row["x2"]) <= left + crop_width - margin
        and float(row["y1"]) >= top + margin
        and float(row["y2"]) <= top + crop_height - margin
    )


def choose_encoder(requested: str) -> tuple[str, list[str]]:
    if requested != "auto":
        return requested, encoder_arguments(requested)
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        check=True,
    )
    encoder = "h264_nvenc" if "h264_nvenc" in result.stdout else "libx264"
    return encoder, encoder_arguments(encoder)


def encoder_arguments(encoder: str) -> list[str]:
    if encoder == "h264_nvenc":
        return [
            "-c:v",
            encoder,
            "-preset",
            "p6",
            "-tune",
            "hq",
            "-rc",
            "vbr",
            "-cq",
            "19",
            "-b:v",
            "0",
        ]
    if encoder == "libx264":
        return ["-c:v", encoder, "-preset", "medium", "-crf", "18"]
    raise ValueError(f"Unsupported encoder: {encoder}")


def camera_plan_rows(
    job: SongJob, keys: tuple[CameraKey, ...], base_x: float, base_y: float
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for second in np.arange(0.0, job.duration, 1.0):
        offset_x, offset_y = camera_offset(float(second), keys)
        rows.append(
            {
                "relative_seconds": f"{second:.3f}",
                "absolute_seconds": f"{job.clip_start + second:.3f}",
                "section": camera_section(float(second), keys),
                "center_x": f"{base_x + offset_x:.6f}",
                "center_y": f"{base_y + offset_y:.6f}",
                "crop_width": 1792,
                "crop_height": 1008,
                "dynamic_zoom": False,
            }
        )
    return rows


def render_command(
    source_video: Path,
    source_audio: Path,
    output_path: Path,
    filter_path: Path,
    job: SongJob,
    encoder_args: list[str],
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-nostats",
        "-stats_period",
        "1",
        "-init_hw_device",
        "vulkan=vk:0",
        "-filter_hw_device",
        "vk",
        "-ss",
        f"{job.clip_start:.6f}",
        "-i",
        str(source_video),
        "-ss",
        f"{job.clip_start:.6f}",
        "-i",
        str(source_audio),
        "-filter_complex_script",
        str(filter_path),
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-t",
        f"{job.duration:.6f}",
        *encoder_args,
        "-pix_fmt",
        "yuv420p",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-c:a",
        "aac",
        "-b:a",
        "256k",
        "-ar",
        "48000",
        "-progress",
        "pipe:1",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def run_render(command: list[str], log_path: Path, duration: float) -> float:
    started = time.perf_counter()
    with log_path.open("w", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=log_handle,
            text=True,
            encoding="utf-8",
        )
        assert process.stdout is not None
        next_report = 30.0
        for raw_line in process.stdout:
            key, separator, value = raw_line.strip().partition("=")
            if separator and key == "out_time":
                current = parse_progress_time(value)
                if current is not None and current >= next_report:
                    print(f"rendered {current:.1f}/{duration:.1f} seconds", flush=True)
                    next_report += 30.0
        return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(
            f"FFmpeg failed with exit code {return_code}; inspect {log_path}"
        )
    return time.perf_counter() - started


def parse_progress_time(value: str) -> float | None:
    parts = value.split(":")
    if len(parts) != 3:
        return None
    return int(parts[0]) * 3600.0 + int(parts[1]) * 60.0 + float(parts[2])


def motion_metrics(
    job: SongJob, keys: tuple[CameraKey, ...], fps: float
) -> dict[str, float]:
    times = np.arange(0.0, job.duration, 1.0 / fps)
    centers = np.asarray([camera_offset(float(value), keys) for value in times])
    velocity = np.diff(centers, axis=0)
    acceleration = np.diff(velocity, axis=0)
    return {
        "max_pan_delta_per_frame_source_pixels": float(
            np.linalg.norm(velocity, axis=1).max()
        ),
        "max_pan_acceleration_source_pixels": float(
            np.linalg.norm(acceleration, axis=1).max()
        ),
        "horizontal_span_source_pixels": float(np.ptp(centers[:, 0])),
        "vertical_span_source_pixels": float(np.ptp(centers[:, 1])),
    }


def render_job(
    job: SongJob,
    source_video: Path,
    source_audio: Path,
    model_path: Path,
    output_root: Path,
    info: dict[str, object],
    args: argparse.Namespace,
) -> dict[str, object]:
    job_dir = output_root / f"{job.interval_no:02d}_{safe_filename(job.title)}"
    job_dir.mkdir(parents=True, exist_ok=True)
    ass_path, timeline_path, fonts_dir = write_subtitles(job, job_dir, args.credit)
    keys = build_camera_keys(job)
    detections_path = job_dir / "character_detections.csv"
    if args.reuse_detections and detections_path.exists():
        detections = read_csv(detections_path)
        for row in detections:
            row["detected"] = row["detected"].lower() == "true"
    else:
        detections = detect_character(
            source_video,
            model_path,
            job,
            float(info["fps"]),
            args.sample_seconds,
            args.detector_confidence,
            args.device,
        )
        write_csv(detections_path, detections)
    detector = detection_summary(
        detections, keys, int(info["width"]), int(info["height"]), 1792, 1008
    )
    (job_dir / "character_detection_summary.json").write_text(
        json.dumps(detector, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    base_x, base_y = (float(value) for value in detector["camera_base_center"])
    write_csv(
        job_dir / "camera_timeline.csv", camera_plan_rows(job, keys, base_x, base_y)
    )
    output_path = (
        job_dir
        / f"{job.interval_no:02d}_{safe_filename(job.title)}_MV_Lite_1080p60.mp4"
    )
    graph = build_filter_graph(
        job=job,
        camera_keys=keys,
        base_x=base_x,
        base_y=base_y,
        crop_width=1792,
        crop_height=1008,
        subtitle_path=ass_path,
        fonts_dir=fonts_dir,
        mask_ui=not args.no_ui_mask,
    )
    filter_path = job_dir / "filter_graph.txt"
    filter_path.write_text(graph, encoding="utf-8")
    encoder, encoder_args = choose_encoder(args.encoder)
    command = render_command(
        source_video, source_audio, output_path, filter_path, job, encoder_args
    )
    render_seconds = 0.0
    if not (args.reuse_output and can_reuse_output(output_path, job.duration)):
        render_seconds = run_render(command, job_dir / "ffmpeg.log", job.duration)
    summary = {
        "interval_no": job.interval_no,
        "title": job.title,
        "source_video": str(source_video),
        "source_audio": str(source_audio),
        "output": str(output_path),
        "clip_start_seconds": job.clip_start,
        "clip_end_seconds": job.clip_end,
        "duration_seconds": job.duration,
        "source_resolution": [int(info["width"]), int(info["height"])],
        "output_resolution": [1920, 1080],
        "fps": float(info["fps"]),
        "fixed_crop": [1792, 1008],
        "constant_scale": 1920 / 1792,
        "dynamic_zoom": False,
        "image_correction": "none",
        "camera_motion": "smootherstep section keys plus continuous low-frequency x/y drift",
        "subtitle_events": len(job.lyrics),
        "subtitle_overlap_count": sum(
            left.absolute_end > right.absolute_start
            for left, right in zip(job.lyrics, job.lyrics[1:])
        ),
        "subtitle_timeline": str(timeline_path),
        "character_detection": detector,
        "encoder": encoder,
        "render_seconds": render_seconds,
        **motion_metrics(job, keys, float(info["fps"])),
    }
    (job_dir / "render_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def validate_inputs(
    args: argparse.Namespace, info: dict[str, object], jobs: Iterable[SongJob]
) -> None:
    required = [args.video, args.audio, args.intervals, args.phrases, args.model]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing input files: {missing}")
    if (int(info["width"]), int(info["height"])) != (1920, 1080):
        raise ValueError(
            f"Expected native 1920x1080 source, got {info['width']}x{info['height']}"
        )
    if abs(float(info["fps"]) - 60.0) > 0.01:
        raise ValueError(f"Expected 60 fps source, got {info['fps']}")
    for job in jobs:
        if job.clip_end > float(info["duration"]) + 0.1:
            raise ValueError(f"Interval {job.interval_no} ends after the source video")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render no-token MV-Lite videos from existing song intervals and phrase labels."
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--intervals", type=Path, required=True)
    parser.add_argument("--phrases", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--interval-no", type=int, action="append", dest="interval_nos")
    parser.add_argument("--credit", default="Cover 帕蘿妮 Paroniie")
    parser.add_argument("--sample-seconds", type=float, default=2.0)
    parser.add_argument("--detector-confidence", type=float, default=0.20)
    parser.add_argument("--device", default="0")
    parser.add_argument(
        "--encoder", choices=("auto", "h264_nvenc", "libx264"), default="auto"
    )
    parser.add_argument("--reuse-detections", action="store_true")
    parser.add_argument("--reuse-output", action="store_true")
    parser.add_argument("--no-ui-mask", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.video = args.video.resolve()
    args.audio = args.audio.resolve()
    args.intervals = args.intervals.resolve()
    args.phrases = args.phrases.resolve()
    args.model = args.model.resolve()
    args.output_dir = args.output_dir.resolve()
    selected = set(args.interval_nos) if args.interval_nos else None
    jobs = load_jobs(args.intervals, args.phrases, selected)
    info = probe_video(args.video)
    validate_inputs(args, info, jobs)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries = [
        render_job(job, args.video, args.audio, args.model, args.output_dir, info, args)
        for job in jobs
    ]
    batch = {"requested": len(jobs), "rendered": len(summaries), "outputs": summaries}
    (args.output_dir / "batch_render_summary.json").write_text(
        json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(batch, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
