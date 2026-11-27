---
name: minimax-h3-turbo-fal-idle-loop
description: >-
  Use when generating a five-second idle loop MP4 from one PNG/JPEG with
  MiniMax H3 Max on fal at 768P, with a pure-white background by default or
  with the source scene preserved. First-frame-only I2V (no end keyframe).
  Trigger on H3 idle loop, H3 Turbo idle loop, fal idle video, 單圖待機循環影片,
  有背景待機循環. Not for Ref2VA video editing or upscaling.
---

# MiniMax H3 Max · fal Idle Loop

一張 PNG／JPEG → 首幀 I2V → 5 秒待機 MP4。使用同目錄的 `direct_idle.py`，Python 3 標準函式庫即可；不需 ffmpeg、其他 repo、ComfyUI、OpenRouter 或本機模型。

## 執行

正式生成需要本機圖片、環境變數 `FAL_KEY`（帳戶有額度）及可連至 fal 的網路。請保護金鑰，腳本不會自動載入 `.dev.vars`。執行前請自行核對像素尺寸，腳本不會檢查、縮放或裁切。`--dry-run` 只印出請求內容，使用帶有圖片副檔名的佔位路徑即可。

### INPUT_IMAGE 尺寸（必要）

- `INPUT_IMAGE` 必須與預期輸出影片的像素尺寸完全相同（同寬 × 同高），只有長寬比相同並不足夠。執行前先檢查圖片尺寸；不符時先在技能外準備符合尺寸的圖片。
- 本技能直式（約 9:16）、`resolution="768P"` 的配方，`INPUT_IMAGE` 必須準備為 **768×1344 px（寬×高）**。這是實測的輸出尺寸，實際比例為 4:7，並非精確 9:16；不要改用 768×1365、720×1280 或 1080×1920。
- 768P 的輸出畫布跟隨 `image_url`。兩種模式的 prompt 都要求沿用首幀構圖與長寬比，原先的 `in 9:16` 已移除。既有 2:3 輸入案例的輸出為 **768×1152 px**。使用其他比例前，先確認實際輸出寬高，再將 `INPUT_IMAGE` 準備成相同尺寸。[fal 官方 API 文件](https://fal.ai/models/minimax/h3-max/image-to-video/api)
- 尺寸證據（2026-11-05）：以本技能 `direct_idle.py`、首幀限定、768P、5 秒實跑一次，864×1536（9:16）幾何測試 PNG → provider MP4；`ffprobe` 量得 **768×1344、24 fps**。此輸入刻意用來量測尺寸轉換，未符合上述同尺寸輸入規範。

以本檔所在目錄為 `SKILL_DIR`，將 `INPUT_IMAGE` 換成實際圖片，`OUTPUT_VIDEO` 選在技能目錄外：

```sh
python3 -B "$SKILL_DIR/direct_idle.py" "$INPUT_IMAGE" "$OUTPUT_VIDEO" --dry-run
python3 -B "$SKILL_DIR/direct_idle.py" "$INPUT_IMAGE" "$OUTPUT_VIDEO" --background scene --dry-run
```

CLI 語法為 `python3 direct_idle.py INPUT [OUTPUT] [--background {white,scene}] [--dry-run]`。省略 `--background` 即為 `white`，也可明確指定 `--background white`。確認要正式生成時，移除 `--dry-run`。省略 `OUTPUT` 時，兩種模式都會使用圖片旁的 `INPUT.idle.mp4`。若需保留兩版，請分別指定輸出路徑。

### 背景模式

- `--background white`（預設）鎖定平坦純白 `#ffffff` 背景，禁止漸層、陰影溢出、新道具或環境變化。提示詞在 [prompts/white.txt](prompts/white.txt)。
- `--background scene`（有背景）要求背景從首幀到末幀與 Picture 1 完全一致，保留既有背景的顏色、道具與光線。適用真實場景、純黑底與純白底。提示詞在 [prompts/scene.txt](prompts/scene.txt)。
- 使用 `scene` 時，若 PNG 帶透明通道，請先合成到不透明底再上傳。fal／H3 似乎會忽略 alpha，透明區域底下殘留的 RGB 可能變成光暈，甚至被補成全新場景。黑底板請用純黑，白底板請用純白。已是不透明的場景圖可直接使用。

腳本從自身所在目錄下的 `prompts/` 讀取 UTF-8 提示詞，因此可從任意工作目錄執行。

## 固定配方與交付

腳本將圖片上傳至 fal storage，只填 `image_url`（不填 `end_image_url`），同步呼叫 `minimax/h3-max/image-to-video`，使用 5 秒、768P 與所選的待機提示詞。兩種模式都固定鏡頭，並維持全程循環的呼吸、眨眼、髮絲擺動、胸腔與軀幹的輕微慣性、髖部重心轉移與下肢微動。從 `result.video.url` 下載的 MP4 即為最終檔，無後處理。

- 成功後確認 MP4 存在且非空，核對輸出影片與 `INPUT_IMAGE` 的像素寬高一致，再透過目前介面附上 MP4／artifact，並提供可用的檔案路徑。若尺寸不符，回報實際輸入／輸出尺寸，不可宣稱已符合本技能的尺寸規範。
- `<OUTPUT>.result.json` 保存 provider 回應。若只有下載失敗，從其中的 `video.url` 取回影片，不要重新生成。生成逾時／失敗不自動重送。
- 輸出、JSON 與測試素材放在技能目錄外。
