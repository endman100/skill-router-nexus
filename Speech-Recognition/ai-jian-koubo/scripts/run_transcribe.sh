#!/usr/bin/env bash
# Consume one normalized ASR Router result and prepare AI剪口播 artifacts.

set -euo pipefail

VIDEO_PATH="${1:-}"
BASE_DIR="${2:-.}"
shift $(( $# >= 2 ? 2 : $# ))
ASR_RESULT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --asr-result)
      ASR_RESULT="${2:-}"
      shift 2
      ;;
    *)
      echo "未知参数: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$VIDEO_PATH" || -z "$ASR_RESULT" ]]; then
  echo "用法: $0 <video.mp4> [base_output_dir] --asr-result <normalized-result.json>" >&2
  echo "请先由 Agent 调用 asr-router，再把其 normalized result 传给本脚本。" >&2
  exit 2
fi
if [[ ! -f "$VIDEO_PATH" ]]; then
  echo "视频文件不存在: $VIDEO_PATH" >&2
  exit 1
fi
if [[ ! -f "$ASR_RESULT" ]]; then
  echo "ASR Router 结果不存在: $ASR_RESULT" >&2
  exit 1
fi
for cmd in ffmpeg node; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "缺少依赖: $cmd" >&2; exit 1; }
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TRANSCRIBE_DIR="$BASE_DIR/1_转录"
mkdir -p "$TRANSCRIBE_DIR"

echo "步骤1: 提取音频..."
ffmpeg -i "file:$VIDEO_PATH" -vn -acodec libmp3lame -y "$TRANSCRIBE_DIR/audio.mp3" 2>/dev/null

SOURCE_RESULT="$(cd "$(dirname "$ASR_RESULT")" && pwd)/$(basename "$ASR_RESULT")"
TARGET_RESULT="$(cd "$TRANSCRIBE_DIR" && pwd)/asr-result.json"
if [[ "$SOURCE_RESULT" != "$TARGET_RESULT" ]]; then
  cp "$SOURCE_RESULT" "$TARGET_RESULT"
fi

echo "步骤2: 消费 ASR Router normalized result..."
node "$SCRIPT_DIR/generate_subtitles.js" "$TARGET_RESULT" "" "$TRANSCRIBE_DIR"

echo "完成: $TRANSCRIBE_DIR"
