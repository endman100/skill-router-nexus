---
name: minimax-h3-turbo-fal-idle-loop
description: >-
  Use when generating a five-second idle loop MP4 from one PNG/JPEG with
  MiniMax H3 Max Turbo on fal. Reuses the same image as first and last frame
  for subtle breathing and blinking. Trigger on H3 Turbo idle loop, fal idle
  video, 單圖待機循環影片. Not for Ref2VA video editing or upscaling.
---

# MiniMax H3 Turbo · fal Idle Loop

一張 PNG／JPEG → 相同首尾圖 → 5 秒待機 MP4。使用同目錄的 `direct_idle.py`，Python 3 標準函式庫即可；不需其他 repo、ComfyUI、OpenRouter 或本機模型。

## 執行

需要使用者提供的本機圖片、環境變數 `FAL_KEY`（帳戶有額度）及可連至 fal 的網路。不要輸出金鑰；腳本不會自動載入 `.dev.vars`。圖片建議 9:16，720×1280 非硬性要求；腳本不縮放或裁切。

以本檔所在目錄為 `SKILL_DIR`，將 `INPUT_IMAGE` 換成實際圖片，`OUTPUT_VIDEO` 選在技能目錄外：

```sh
python3 -B "$SKILL_DIR/direct_idle.py" "$INPUT_IMAGE" "$OUTPUT_VIDEO" --dry-run
python3 -B "$SKILL_DIR/direct_idle.py" "$INPUT_IMAGE" "$OUTPUT_VIDEO"
```

CLI：`python3 direct_idle.py INPUT [OUTPUT] [--dry-run]`。省略 OUTPUT 時，輸出在圖片旁的 `INPUT.idle.mp4`。`--dry-run` 不需要 key、不發網路請求；僅問說明、封裝或預覽時使用它。使用者要求生成且輸入齊全時，直接執行生成命令。

## 固定配方與交付

腳本將圖片上傳至 fal storage，以同一個 URL 填入 `image_url`／`end_image_url`，同步呼叫 `minimax/h3-max-turbo/image-to-video`，使用內嵌原始 Idle prompt、5 秒、480P，再下載 `result.video.url`。prompt 固定鏡頭，只允許細微呼吸與眨眼；來源為 `endman100/h3-chat-system` 提交 `52b2837` 的 `templates.idle_loop_h3`，無外部檔案相依。

- 成功後確認 MP4 存在且非空，透過目前介面附上 MP4／artifact，並提供可用的檔案路徑。
- `<OUTPUT>.result.json` 保存 provider 回應。若只有下載失敗，從其中的 `video.url` 取回影片，不要重新生成。生成逾時／失敗不自動重送；回報錯誤並先核對供應商結果，避免重複付費。
- 相同首尾圖不保證接縫完美；H3 request 未明確關閉音軌，不宣稱下載檔一定靜音。輸出、JSON 與測試素材放在技能目錄外。
