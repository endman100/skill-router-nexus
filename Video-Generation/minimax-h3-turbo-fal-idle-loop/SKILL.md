---
name: minimax-h3-turbo-fal-idle-loop
description: >-
  Use when generating a five-second idle loop MP4 from one PNG/JPEG with
  MiniMax H3 Max on fal at 768P. First-frame-only I2V (no end keyframe); provider
  MP4 is the final output. Trigger on H3 idle loop, H3 Turbo idle loop, fal idle
  video, 單圖待機循環影片. Not for Ref2VA video editing or upscaling.
---

# MiniMax H3 Max · fal Idle Loop

一張 PNG／JPEG → 首幀 I2V → 5 秒待機 MP4。使用同目錄的 `direct_idle.py`，Python 3 標準函式庫即可；不需 ffmpeg、其他 repo、ComfyUI、OpenRouter 或本機模型。

## 執行

需要使用者提供的本機圖片、環境變數 `FAL_KEY`（帳戶有額度）及可連至 fal 的網路。不要輸出金鑰；腳本不會自動載入 `.dev.vars`。腳本不縮放或裁切，也不會自動檢查像素尺寸。

### INPUT_IMAGE 尺寸（必要）

- `INPUT_IMAGE` 必須與預期輸出影片的像素尺寸完全相同（同寬 × 同高），只有長寬比相同並不足夠。執行前先檢查圖片尺寸；不符時先在技能外準備符合尺寸的圖片。
- 本技能直式（約 9:16）、`resolution="768P"` 的配方，`INPUT_IMAGE` 必須準備為 **768×1344 px（寬×高）**。這是實測的輸出尺寸，實際比例為 4:7，並非精確 9:16；不要改用 768×1365、720×1280 或 1080×1920。
- 768P 不是所有輸入都固定輸出 768×1344。[fal 官方 API 文件](https://fal.ai/models/minimax/h3-max/image-to-video/api) 說明輸出畫布跟隨 `image_url`；比例由首幀圖片決定，prompt 寫 9:16 不會覆蓋它。既有 2:3 輸入案例的輸出為 **768×1152 px**。使用其他比例前須另確認實際輸出寬高，再將 `INPUT_IMAGE` 準備成相同尺寸；不要套用未驗證的縮放或取整公式。
- 尺寸證據（2026-11-05）：以本技能 `direct_idle.py`、首幀限定、768P、5 秒實跑一次，864×1536（9:16）幾何測試 PNG → provider MP4；`ffprobe` 量得 **768×1344、24 fps**。此輸入刻意用來量測尺寸轉換，未符合上述同尺寸輸入規範。

以本檔所在目錄為 `SKILL_DIR`，將 `INPUT_IMAGE` 換成實際圖片，`OUTPUT_VIDEO` 選在技能目錄外：

```sh
python3 -B "$SKILL_DIR/direct_idle.py" "$INPUT_IMAGE" "$OUTPUT_VIDEO" --dry-run
python3 -B "$SKILL_DIR/direct_idle.py" "$INPUT_IMAGE" "$OUTPUT_VIDEO"
```

CLI：`python3 direct_idle.py INPUT [OUTPUT] [--dry-run]`。省略 OUTPUT 時，輸出在圖片旁的 `INPUT.idle.mp4`。下載回來的 provider MP4 即最終檔，無後處理。

## 固定配方與交付

腳本將圖片上傳至 fal storage，只填 `image_url`（不填 `end_image_url`），同步呼叫 `minimax/h3-max/image-to-video`，使用內嵌角色無關 Idle prompt、5 秒、768P，再下載 `result.video.url`。prompt 固定鏡頭與純白背景 `#ffffff`，允許較明顯全身體機：呼吸／眨眼／髮絲／胸腔軟體慣性＋髖部左右微搖與下肢微動，全程持續動。

- 成功後確認 MP4 存在且非空，核對輸出影片與 `INPUT_IMAGE` 的像素寬高一致，再透過目前介面附上 MP4／artifact，並提供可用的檔案路徑。若尺寸不符，回報實際輸入／輸出尺寸，不可宣稱已符合本技能的尺寸規範。
- `<OUTPUT>.result.json` 保存 provider 回應。若只有下載失敗，從其中的 `video.url` 取回影片，不要重新生成。生成逾時／失敗不自動重送。
- 輸出、JSON 與測試素材放在技能目錄外。
