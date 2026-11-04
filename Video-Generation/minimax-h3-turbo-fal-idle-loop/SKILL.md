---
name: minimax-h3-turbo-fal-idle-loop
description: >-
  Use when generating a five-second idle loop MP4 from one PNG/JPEG with
  fal ByteDance Seedance 2.5 image-to-video first/last frame (same image both
  ends) at 720p. Trigger on H3 idle loop, Seedance 2.5 idle, fal FL frame idle,
  單圖待機循環影片. Not for Ref2VA video editing or upscaling.
---

# Seedance 2.5 · fal First/Last Frame Idle Loop

一張 PNG／JPEG → 相同 URL 填 `image_url`／`end_image_url` → 5 秒待機 MP4。使用同目錄的 `direct_idle.py`，Python 3 標準函式庫即可；不需其他 repo、ComfyUI、OpenRouter 或本機模型。

## 執行

需要使用者提供的本機圖片、環境變數 `FAL_KEY`（帳戶有額度）及可連至 fal 的網路。不要輸出金鑰；腳本不會自動載入 `.dev.vars`。圖片建議 9:16；腳本不縮放或裁切。

以本檔所在目錄為 `SKILL_DIR`，將 `INPUT_IMAGE` 換成實際圖片，`OUTPUT_VIDEO` 選在技能目錄外：

```sh
python3 -B "$SKILL_DIR/direct_idle.py" "$INPUT_IMAGE" "$OUTPUT_VIDEO" --dry-run
python3 -B "$SKILL_DIR/direct_idle.py" "$INPUT_IMAGE" "$OUTPUT_VIDEO"
```

CLI：`python3 direct_idle.py INPUT [OUTPUT] [--dry-run] [--resolution 480p|720p|1080p]`。省略 OUTPUT 時，輸出在圖片旁的 `INPUT.idle.mp4`。預設 `720p`、`generate_audio=false`、`duration=5`。

## 固定配方與交付

腳本將圖片上傳至 fal storage，以同一個 URL 填入 first／last frame，同步呼叫 `bytedance/seedance-2.5/image-to-video`。prompt 沿用角色無關全身 idle（呼吸／眨眼／髮絲／胸腔軟體慣性＋髖部左右微搖與下肢微動），背景鎖 `#ffffff`，鏡頭鎖死。

- 成功後確認 MP4 存在且非空，透過目前介面附上 MP4／artifact，並提供可用的檔案路徑。
- `<OUTPUT>.result.json` 保存 provider 回應。若只有下載失敗，從其中的 `video.url` 取回影片，不要重新生成。生成逾時／失敗不自動重送。
- 相同首尾靜圖仍可能末段偏靜；接縫與動作品質看成片。輸出、JSON 與測試素材放在技能目錄外。
