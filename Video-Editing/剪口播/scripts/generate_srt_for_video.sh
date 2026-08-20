#!/usr/bin/env bash
# Build raw SRT from a finished video and an Agent-produced ASR Router result.

set -euo pipefail

VIDEO_PATH="${1:-}"
OUTPUT_DIR="${2:-}"
ASR_RESULT="${3:-}"

if [[ -z "$VIDEO_PATH" || -z "$OUTPUT_DIR" || -z "$ASR_RESULT" ]]; then
  echo "用法: generate_srt_for_video.sh <video.mp4> <subtitle_output_dir> <asr-result.json>" >&2
  echo "请先由 Agent 对该视频调用 asr-router，再传入 normalized result。" >&2
  exit 2
fi
[[ -f "$VIDEO_PATH" ]] || { echo "找不到视频文件: $VIDEO_PATH" >&2; exit 1; }
[[ -f "$ASR_RESULT" ]] || { echo "找不到 Router 结果: $ASR_RESULT" >&2; exit 1; }

mkdir -p "$OUTPUT_DIR/1_转录" "$OUTPUT_DIR/3_输出"
ffmpeg -y -v error -i "file:$VIDEO_PATH" -vn -acodec libmp3lame "$OUTPUT_DIR/1_转录/audio.mp3"

SOURCE_RESULT="$(cd "$(dirname "$ASR_RESULT")" && pwd)/$(basename "$ASR_RESULT")"
TARGET_RESULT="$(cd "$OUTPUT_DIR/1_转录" && pwd)/asr-result.json"
if [[ "$SOURCE_RESULT" != "$TARGET_RESULT" ]]; then
  cp "$SOURCE_RESULT" "$TARGET_RESULT"
fi

node - "$TARGET_RESULT" "$OUTPUT_DIR" <<'NODE'
const fs = require('fs');
const resultPath = process.argv[2];
const outputDir = process.argv[3];
const result = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
if (!result.schema_version || !Array.isArray(result.segments)) {
  throw new Error('输入不是 ASR Router normalized result');
}
const subtitles = result.segments
  .map((segment, index) => ({
    id: index + 1,
    text: String(segment.text || '').trim(),
    start: Number(segment.start),
    end: Number(segment.end),
  }))
  .filter(item => item.text && Number.isFinite(item.start) && Number.isFinite(item.end) && item.start >= 0 && item.end >= item.start);
if (subtitles.length === 0) {
  throw new Error('Router 结果没有可用的 segment timestamps');
}
fs.writeFileSync(`${outputDir}/subtitles_with_time.json`, JSON.stringify(subtitles, null, 2));

function toSRT(sec) {
  const milliseconds = Math.max(0, Math.round(sec * 1000));
  const h = Math.floor(milliseconds / 3600000);
  const m = Math.floor((milliseconds % 3600000) / 60000);
  const s = Math.floor((milliseconds % 60000) / 1000);
  const ms = milliseconds % 1000;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}
const srt = subtitles.map((item, index) => {
  const text = item.text.replace(/[。！？]+$/g, '');
  return `${index + 1}\n${toSRT(item.start)} --> ${toSRT(item.end)}\n${text}`;
}).join('\n\n');
fs.writeFileSync(`${outputDir}/3_输出/video.raw.srt`, srt.trim() + '\n');
console.log(`已生成 ${subtitles.length} 条转写初稿`);
NODE

echo "Raw SRT: $OUTPUT_DIR/3_输出/video.raw.srt"
