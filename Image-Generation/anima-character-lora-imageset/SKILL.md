---
name: anima-character-lora-imageset
description: >-
  用角色 LoRA（自己訓練的，或 civitai 上的 Anima 角色 LoRA）在 Anima 批量生成姿勢圖冊，每個動作同時產出有衣服與無衣服兩版。
  適用於拿角色 LoRA 生成各動作圖冊、或為後續影片生成準備圖片時。
---

# Anima 角色 LoRA 圖冊

> Agent 請勿讀取 `templates/template.json`、`templates/actions.json`、`templates/workflow_api.json`，直接執行 `scripts/gen.py` 即可。

0. 先找到可使用的 ComfyUI（服務有開、queue 是空的）。`gen.py` 預設連 `127.0.0.1:8188`，要在能連到該 ComfyUI 的機器上執行。
1. 找角色資料：trigger、角色外觀 tag、服裝 tag、建議權重（預設 0.8）。civitai 的 LoRA 要先確認 Base Model 是 Anima。
2. 下載 LoRA，放進 ComfyUI 的 `loras` 目錄。
3. 複製 `templates/character.example.json`，填入角色資料。
4. 執行：

```
python3 scripts/gen.py my_char.json
```
