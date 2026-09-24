---
name: rewrite-qwen2-1-prompts
description: "Rewrite text-to-image requests and image-editing instructions using the Qwen-Image-2.1 Prompt Enhancer method. Use for rewrite-Qwen2.1-prompts, image prompt rewrite, prompt rewrite, image edit prompt, text-to-image prompt expansion, 擴寫、重寫或優化生圖提示詞, 提示詞重寫, 改圖提示詞, Qwen Image prompt-rewrite, or determining wh_ratio/ratio_follow. Supports text-only t2i and edit tasks with 1..N input images; returns strict JSON and does not generate the image itself."
---

# rewrite-Qwen2.1-prompts

使用本 skill 重寫圖片生成或圖片編輯需求。詳細規則以 bundled upstream system prompt 為真源；需要精確復現方法時，先完整讀取對應 reference，不要只靠摘要或記憶。

## 工作流程

1. 先判定任務：
   - **t2i**：只有文字需求，目標是把簡短或模糊的生圖需求擴寫為完整成品描述。
   - **edit**：有 1..N 張輸入圖片，目標是把編輯需求改寫成可執行且不歧義的編輯指令。
2. t2i 時完整讀取 [references/system_prompt_t2i.txt](references/system_prompt_t2i.txt)，嚴格套用其中的八步流程、文字保真、構圖展開、比例選擇與 JSON 輸出規則。
3. edit 時先實際檢視所有輸入圖片，再完整讀取 [references/system_prompt_edit.txt](references/system_prompt_edit.txt)。維持輸入圖片順序；多圖引用固定使用 `<image1>`, `<image2>` ...，不得自行重排。
4. 把使用者已明確指定的文字、數量、顏色、位置、比例與保留條件視為硬約束。對 t2i，可依 system prompt 補全未指定的畫面；對 edit，只改動使用者指定的屬性，未指定內容以輸入圖為基準保留。
5. 僅輸出對應任務的 JSON；不要加說明、markdown code fence、問候或額外欄位。
6. 交付前驗證 JSON 可解析、欄位完整、圖片內文字未被改寫、比例欄位符合契約。

## 輸出契約

t2i 必須只有兩個欄位：

```json
{"rewritten_prompt":"<single-paragraph finished-image description>","wh_ratio":"<W:H>"}
```

edit 必須只有三個欄位：

```json
{"rewritten_prompt":"<single-paragraph editing directive>","wh_ratio":"<W:H or empty>","ratio_follow":"<<imageX> or empty>"}
```

edit 的 `wh_ratio` 與 `ratio_follow` 互斥：一個有值時另一個必須是空字串。單圖局部編輯通常沿用輸入圖比例；新構圖、明確指定比例或擴圖則依 upstream 規則決定 `wh_ratio`。

## 與上游 Prompt Enhancer checkpoint 的關係

需要執行上游模型本身，而不是由目前 agent 依規則重寫時，使用正確配對：

- t2i：`Qwen/Qwen-Image-2.1-PE-T2I` + `system_prompt_t2i.txt`
- edit：`Qwen/Qwen-Image-2.1-PE-I2I` + `system_prompt_edit.txt`

兩個 checkpoint 與兩份 system prompt 不可互換，也不要合併成一份 prompt。上游 README 明確指出一般的官方 Qwen3.5-VL 9B base model 未針對這兩個回答契約訓練，不能假設會穩定輸出預期 JSON。若透過上游程式執行，遵循其 README 的 inference 設定與 thinking-enabled 要求，但最終仍只向使用者交付所需 JSON，不揭露內部推理。

## 邊界

- 本 skill 只做 prompt rewrite，不自動生成或編輯圖片。
- 使用者同時要求成圖時，先完成 rewrite，再把 `rewritten_prompt` 與比例資訊交給適合的圖片生成/編輯工具或 skill。
- edit 任務沒有實際可讀取的輸入圖片時，不假裝看過圖片；說明缺少必要輸入。
- t2i 不接受輸入圖片作為內容條件；需要圖片參考或修改原圖時改走 edit。
- 不自行增加 negative prompt；上游 prompt enhancer 的回答契約不包含它。

## 上游來源與授權

本 skill 內的兩份 system prompt 為未修改的上游檔案：

- `prompt_rewrite/prompts/system_prompt_t2i.txt`, blob `7fceb851703c22e341b24d562b4575180eec5297`
- `prompt_rewrite/prompts/system_prompt_edit.txt`, blob `424fcfbe2968973c57fe67e3d629df1b0a1e1550`

來源：`QwenLM/Qwen-Image-2.1` 的 `main` branch。上游目前採 Qwen RESEARCH LICENSE AGREEMENT，包含非商業使用與再散布條件。使用或再散布 bundled upstream materials 前，閱讀本目錄的 `LICENSE.qwen.txt` 與 `NOTICE`。
