---
name: minimax-h3-clothing-adjust
description: >-
  Use when editing wardrobe/outfit on an existing MiniMax H3 Ref2VA clip while
  keeping identity, camera, pose, motion, background, and soundtrack. ComfyUI
  hybrid ref+keyframe graph with partial denoise for clothing-only changes.
  Trigger on H3 clothing adjust, outfit swap, wardrobe edit, change clothes on
  video, Ref2VA clothing retention. Not for from-scratch T2V or Open-H3 2K upscale.
---

# MiniMax H3 · 衣物／造型調整（Ref2VA）

**用途：** 在既有 Ref2VA 參考影片上**只改衣物／造型**，其餘（身份、臉、髮型輪廓、體型、背景、構圖、運鏡、動作時序、音軌）盡量保留。這是 **wardrobe / outfit adjustment** 工作流說明，不是從零生成。

## 何時用

- 使用者已有 `<Video 1>`（及可選 `<Audio 1>`），要換穿著、外套、配色、配件等。
- 需要 MiniMax H3 **Ref2VA** 六段式（`subject_definitions` / `summary` / `retention_analysis` / `detailed_description` / `overall_soundscape` / `non_diegetic_music`）並強調 **attribute_transfer → clothing only**。

勿與 [open-h3-regenerate-2k](../open-h3-regenerate-2k/SKILL.md)（草稿→2K 放大）混淆。

## Workflow

載入：`references/minimax-h3-clothing-adjust-ref2va.json`

圖內要點（接線與模型檔名維持原圖；**僅示範 prompt 已改成衣物調整語氣**）：

1. `VHS_LoadVideo` → 參考片；音訊進 audio VAE；畫面可經 resize 後進 hybrid ref。
2. `MiniMaxH3HybridRefAndKeyframe`：`ref_videos` / `ref_audios` + 可編輯提示詞（節點「④ 衣物調整提示詞」）。
3. 採樣：`SamplerCustomAdvanced`；scheduler 常用 **denoise &lt; 1**（圖內示範約 **0.8**）做部分重繪，較利於保留構圖與動作。
4. 音訊側可用 mask **凍結**（圖內 SolidMask value=0）避免亂改原曲。
5. `CreateVideo` / `SaveVideo` 輸出。

可選 LoRA／替代 UNET／CLIP 節點若存在於圖中，**預設可能為 bypass（mode 4）**——啟用前自行確認；本 skill 不強制那些旁路權重。

## Prompt 寫法（衣物調整）

保留 Ref2VA 標籤結構，重點句子：

- `<Video 1>`：sole visual reference；preserve composition / camera / pose / motion / identity。
- 明確寫 **Change clothing/outfit only**；`retention_analysis` 對 `<Subject 1>` 用 `attribute_transfer`（wardrobe），背景與運鏡 `fully_preserved`，音樂 `fully_copy`。
- 具體目標服裝寫在 `detailed_description`（材質、顏色、層次、與動作的布料動態）。
- 風格：HD realistic photoreal；禁止無端改成 anime／2D。

圖內附示範英文 prompt（已去敏感描述）；實務請依目標服裝改寫，**不要**把放大／重生任務的散文 prompt 直接貼進來。

## 檢查清單

- [ ] 參考影音路徑已換成當次素材  
- [ ] Prompt 只描述衣物變更 + 保留條款  
- [ ] Denoise / mask 設定符合「只動服裝、音軌凍結」意圖  
- [ ] 輸出前確認未誤開與衣物無關的旁路 LoRA  

## Needs

ComfyUI + MiniMax H3 Ref2VA 相關節點（Hybrid RefAndKeyframe、音視頻 VAE、LTXVConcatAVLatent 等）與圖內載入的 checkpoint／encoder 檔名。
