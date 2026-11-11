---
name: streamerase
description: "StreamErase（zhuobai/StreamErase）的即時串流影片物件消除與修補方法。用於 video object removal、streaming video erasing、video inpainting、遮罩式影片消除、長影片背景補全，以及查詢官方權重、安裝、短／長影片推論、硬體需求與發布限制。"
---

# StreamErase

## 摘要與適用情境

[StreamErase: Towards Ultra-Fast Streaming Video Erasing](https://arxiv.org/abs/2610.20137) 以 Wan2.1-T2V-1.3B 為基礎，將雙向影片消除模型蒸餾為單步因果模型，使用 sliding-window attention、attention sinks 與 rolling KV cache 支援長影片。輸入來源影片和目標遮罩，移除物件並生成時間一致的背景，也以相關陰影、反射等影響為消除目標。

適合查詢、評估或執行串流影片物件移除；HF 的 `image-to-video` 標籤不代表只需一張圖片。單張圖片的遮罩式消除可參考 [LensErase](../../Image-and-Design/lenserase/SKILL.md)；兩者用途相近，未查得模型衍生關係。

## 發布狀態與執行方式

查核日期：2026-11-11；[官方程式](https://github.com/zhuobaidong/StreamErase) `main`：`55bc2c18ce3f32d820f6fa908e546c28e209de5c`。
HF 檔案清單只有 `.gitattributes`、`README.md`、`StreamErase.pt`（5,676,729,747 bytes，約 5.68 GB）；還需另下載 Wan 基礎模型。

**目前有上游缺檔阻塞：** `inference.py` 和 `inference_long.py` 都引用 `model.wan_vae.AutoencoderKLWan`，但查核版本沒有 `model/`，README 也未說明如何取得該模組。以下保留官方安裝與推論步驟，尚未完成端到端執行驗證；執行前先確認上游已補齊，勿猜測替代模組或宣稱可直接跑通。

取得 repo 後，在其根目錄執行 [README Quick Start](https://github.com/zhuobaidong/StreamErase#quick-start)：

```bash
git clone https://github.com/zhuobaidong/StreamErase.git
cd StreamErase
conda create -n StreamErase python=3.10 -y
conda activate StreamErase
pip install -r requirements.txt
pip install git+https://github.com/openai/CLIP.git
pip install flash-attn --no-build-isolation
python setup.py develop

hf download Wan-AI/Wan2.1-T2V-1.3B --local-dir wan_models/Wan2.1-T2V-1.3B
hf download zhuobai/StreamErase StreamErase.pt --local-dir model_weights

python inference.py \
  --config_path configs/config.yaml \
  --video_dir input/short_video/video \
  --mask_dir input/short_video/mask \
  --output_folder output \
  --checkpoint_path model_weights/StreamErase.pt
```

長影片使用 `inference_long.py`。README 範例漏了 `--num_output_frames`；下例依[官方 parser 說明](https://github.com/zhuobaidong/StreamErase/blob/main/inference_long.py)補上 `63`（標註約 15 秒），其餘參數沿用 README：

```bash
python inference_long.py \
  --config_path configs/config.yaml \
  --video_dir input/long_video/video \
  --mask_dir input/long_video/mask \
  --output_folder output_long \
  --checkpoint_path model_weights/StreamErase.pt \
  --num_output_frames 63
```

- `--num_output_frames` 是 latent frame 數；長影片程式讀取 `4*N-3` 個像素影格，`63` 對應 249 格。短影片預設 `21`，讀取前 81 格。準備至少相應長度、逐格對齊的影片與遮罩。
- 兩個腳本都有預設的移除物件與相關效果之文字提示，可用 `--prompt` 調整；文字不能替代 mask。
- 依賴清單要求 PyTorch ≥ 2.4.0、torchvision ≥ 0.19.0、diffusers 0.31.0；程式使用 CUDA、BF16 與 FlashAttention。最低 VRAM、確切 CUDA 版本、消費級 GPU 速度未公布；程式中的 40 GB 換入換出門檻不是最低顯存需求，CPU 路徑未受支援驗證。

## 輸入與輸出

依[短影片腳本](https://github.com/zhuobaidong/StreamErase/blob/main/inference.py)、[長影片腳本](https://github.com/zhuobaidong/StreamErase/blob/main/inference_long.py)與[讀取函式](https://github.com/zhuobaidong/StreamErase/blob/main/utils/utils.py)：

| 項目 | 規格 |
|---|---|
| 來源影片 | `--video_dir` 內的 `.mp4`、`.avi`、`.mov`、`.mkv`；腳本 resize 至寬 832 × 高 480，按順序取影格，不保留任意來源解析度 |
| 遮罩 | `--mask_dir` 中與來源**同檔名（含副檔名）**的遮罩影片；逐格對齊，灰階 ≥ 240 為白色選取區，黑色為背景；沒有內建自動分割步驟 |
| 輸出 | 在 `--output_folder` 寫入同名影片，固定 16 FPS；未複製來源音軌。建議先用官方 MP4 範例，其他封裝的寫出相容性未驗證 |

## 成果與限制

- [論文 Figure 1、§4](https://arxiv.org/html/2610.20137v1)：單張 **H200** 報告 **26.06 FPS、0.87 秒延遲**；這是作者結果，本 skill 未實測，16 FPS 輸出檔案幀率與推論吞吐量不同。
- Table 1：ROSE-Benchmark PSNR **32.791**、FVD **56.294**；LongErase 包含 80 段各 30 秒的影片，用於評估長時間品質與漂移。
- 論文附錄 F：大幅場景切換、有限訓練資料及必須提供明確遮罩仍是限制；檢查殘留目標、陰影反射、邊界及時間閃爍。
- 方法支援因果串流，但發布的 CLI 先讀取整段檔案並在推論後寫檔，未提供 webcam／RTSP 即時服務；不能由固定 KV 視窗推定 CLI 可處理無限長輸入且總記憶體固定。
- 長影片 CLI 的 `--local_attn_size`、`--sink_size`、`--window_rope` 未傳入 pipeline；目前 pipeline 寫死 local window = 12、sink = 3，勿承諾這些旗標能調整行為。

## 授權與來源

- **StreamErase 程式與權重授權未知**：查核時 GitHub 未附整體 LICENSE，HF README 未宣告 license。部分來源檔的第三方授權註記不能代表整個專案；不能推定可商用或再散布。
- [Wan 基礎模型](https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B)的條款須另核對；專案展示網站頁尾的 CC BY-SA 4.0 不等於模型／程式授權。
- [HF 模型卡與權重](https://huggingface.co/zhuobai/StreamErase)／[檔案清單](https://huggingface.co/zhuobai/StreamErase/tree/main)。
- [GitHub／安裝與推論](https://github.com/zhuobaidong/StreamErase)／[專案頁](https://zhuobaidong.github.io/StreamErase/)。
- [論文](https://arxiv.org/abs/2610.20137)／[全文](https://arxiv.org/html/2610.20137v1)。

分類決策：`KEEP_FLAT`；核心用途是編輯既有影片及串流消除，置於 `Video-Editing`。加入後 24 個 skills，未達大型分類門檻；相鄰 EditaLive 著重人物外觀編輯，fal.ai 影片工具未涵蓋此模型，無重複收錄。
