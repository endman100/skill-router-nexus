---
name: minimax-h3-turbo-fal-idle-loop
description: >-
  Use when generating a five-second idle loop MP4 from one PNG/JPEG with
  MiniMax H3 Max on fal at 768P. Uses first-frame-only (no end keyframe) plus
  a short ffmpeg crossfade so motion stays alive and loops. Trigger on H3 idle
  loop, H3 Turbo idle loop, fal idle video, 單圖待機循環影片. Not for Ref2VA
  video editing or upscaling.
---

# MiniMax H3 Max · fal Idle Loop

一張 PNG／JPEG → 首幀 I2V（**不送** `end_image_url`）→ 0.15s 首尾 crossfade → 5 秒待機 MP4。使用同目錄的 `direct_idle.py`，Python 3 標準函式庫＋系統 `ffmpeg`／`ffprobe`；不需其他 repo、ComfyUI、OpenRouter 或本機模型。

## 為何不送 end_image_url

把同一張靜圖同時當 `end_image_url` 會強制模型在末秒收斂回靜止，看起來不像 loop。此技能改為只給首幀，並用短 ffmpeg 首尾淡入（預設 0.15s；閃爍時用 --no-loop-xfade），接縫才活。

## 執行

需要使用者提供的本機圖片、環境變數 `FAL_KEY`（帳戶有額度）、可連至 fal 的網路，以及 `ffmpeg`／`ffprobe`。不要輸出金鑰；腳本不會自動載入 `.dev.vars`。圖片建議 9:16；腳本不縮放或裁切。

以本檔所在目錄為 `SKILL_DIR`，將 `INPUT_IMAGE` 換成實際圖片，`OUTPUT_VIDEO` 選在技能目錄外：

```sh
python3 -B "$SKILL_DIR/direct_idle.py" "$INPUT_IMAGE" "$OUTPUT_VIDEO" --dry-run
python3 -B "$SKILL_DIR/direct_idle.py" "$INPUT_IMAGE" "$OUTPUT_VIDEO"
```

CLI：`python3 direct_idle.py INPUT [OUTPUT] [--dry-run] [--no-loop-xfade] [--cross 0.5] [--keep-raw]`。省略 OUTPUT 時，輸出在圖片旁的 `INPUT.idle.mp4`。`--dry-run` 不需要 key、不發網路請求。

## 固定配方與交付

腳本將圖片上傳至 fal storage，只填 `image_url`（不填 `end_image_url`），同步呼叫 `minimax/h3-max/image-to-video`，使用內嵌角色無關 Idle prompt、5 秒、768P；下載後預設做 0.15 秒首尾 crossfade（0.5 易閃爍；可用 --no-loop-xfade）。prompt 固定鏡頭與純白背景 `#ffffff`，允許較明顯全身體機：呼吸／眨眼／髮絲／胸腔軟體慣性＋髖部左右微搖與下肢微動，全程持續動。

- 成功後確認 MP4 存在且非空，透過目前介面附上 MP4／artifact，並提供可用的檔案路徑。
- `<OUTPUT>.result.json` 保存 provider 回應。若只有下載失敗，從其中的 `video.url` 取回影片，不要重新生成。生成逾時／失敗不自動重送。
- `--keep-raw` 另存未 crossfade 的 provider 檔為 `<OUTPUT>.raw.mp4`。輸出、JSON 與測試素材放在技能目錄外。
