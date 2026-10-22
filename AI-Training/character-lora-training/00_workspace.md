# 00. 建立 workspace

每個新訓練案例請先建立全新的 `<WS>` = `<workspace root>/<trigger>/`（若已存在則更換 workspace root，不沿用舊案）。後續所有案例檔案皆固定存放於下列位置；`<WS>` 請以絕對路徑替換，各步驟指令均於本技能資料夾執行。

```bash
python -B scripts/ws.py create --workspace <WS> --work "<作品名>" --character "<角色名>" --trigger <trigger> --env <ENV>
```

此指令建立全新的 `<WS>` 與下列目錄（`<WS>` 已存在時會停止），並寫入 `<WS>/project.json`（說明見文末「project.json」）。

```text
<WS>/
├── 01_collect/
│   ├── codex/                    # Codex 收集圖 + sources.json
│   ├── grok/                     # Grok 收集圖 + sources.json
│   └── reference/                # 使用者提供的參考圖（可選）
├── 02_clean/
│   ├── input_mapping.json        # 全部收集圖的唯一檔名 ↔ 原始路徑（含子資料夾）
│   ├── dedup/  dedup.json        # 去重結果
│   ├── sfw/  nsfw/  rating.json  # WD Tagger 分流
│   ├── codex_clean/              # Codex 清理圖、summary.json、rejected.json、Codex log
│   ├── collected_sfw/            # 清理後收集圖（Codex 清理 + Grok 通過的 SFW）
│   └── collected_nsfw/           # Grok 處理通過的 NSFW 收集圖
├── 03_sheet/
│   └── character-sheet.png       # 角色設定圖（04 的參考圖）
├── 04_generate/
│   ├── codex/keep_outfit/        # Codex 維持服裝 N 張
│   ├── codex/change_outfit/      # Codex 換服裝 2N 張
│   ├── codex/missing.json        # 未補齊時才有
│   └── grok/keep_outfit/         # Grok 維持服裝 N 張
├── 05_caption/
│   ├── resized/                  # resize_prep 輸出：<群組>/、_needs_upscale/、resize_manifest.json
│   │   └── _up_codex/  _up_grok/  _up_esrgan/   # 各放大方式的 <群組>/ 輸出
│   ├── images/                   # 編號 SFW 圖 + manifest.json（Codex 打標輸入）
│   ├── images_nsfw/              # 編號 NSFW 圖（只給 Grok）
│   ├── vocab/                    # caption_vocab_params.json、contact_sheets/、names.json、
│   │                             # vocab.schema.json、vocab.json、vocab_summary.md、main_outfit.json
│   ├── captions/                 # codex_caption_v2 --out：json/、txt/、stage_txt/、logs/、summary.json…
│   ├── captions_nsfw/            # 本機 dry-run 的 schemas/、assignment.json、prompts/、params.json；
│   │                             # Grok 寫 json/，caption_convert 驗證後輸出 txt/
│   └── train_set/                # 最終訓練集：圖 + 同名 txt + manifest.json
├── 06_train/                     # train_lora --work-dir
│   ├── kwargs_train.json  config.toml
│   ├── regularization/           # 可選：--reg-dir 的正則化圖
│   ├── images_regularization_1to1/  # 可選：程式自動挑的正則化子集
│   └── models/                   # <trigger>-0000NN.safetensors、<trigger>.safetensors、*-state/、train.log
└── 07_validate/
    ├── prompts/
    │   ├── negative.txt             # 負向 prompt（可選）
    │   └── character_features.txt   # 角色特徵覆寫（可選）
    ├── workflow.json                # 可選；未提供時使用技能模板
    ├── extra_model_paths.yaml       # 從 templates/extra_model_paths.example.yaml 複製
    ├── reconstruction/
    │   ├── reference/              # 選定的訓練 PNG + 同名 txt
    │   ├── lora_test/              # 各 checkpoint × 案例 × seed 圖
    │   ├── test_meta.json
    │   └── checkpoint_comparison_XX.png
    └── scenario/
        ├── prompts.json
        ├── lora_test/              # 各 checkpoint × 情境圖
        ├── test_meta.json
        └── checkpoint_comparison_XX.png
```

`eval_lora.py --workspace "<WS>"` 自動尋找訓練集、詞表與 checkpoints，驗證輸出預設存放於 `07_validate/`。

跨案例共用的環境與模型請存放於 `<ENV>`（可為任意固定位置，首次建立後重複使用，不放入 `<WS>`）：

```text
<ENV>/
├── sd-scripts/  .venv/           # 06 訓練程式與環境
├── esrgan_venv/                  # 05 RealESRGAN 備案環境
├── ComfyUI/                      # 07 驗證用
└── models/                       # wd-eva02-large-tagger-v3/、RealESRGAN_x4plus_anime_6B.pth、
                                  # novaAnimeAM_v6029B.safetensors、qwen_3_06b_base.safetensors、
                                  # qwen_image_vae_train.safetensors、qwen_image_vae.safetensors
```

## project.json

`project.json` 保存 `work`（作品名）、`character`（角色名）、`trigger`、`env`（共用環境的絕對路徑），以及初始為空字串的 `main_outfit_id`（步驟 05 選定主要服裝後寫入）。後續腳本以 `--workspace <WS>` 讀取本案資料與預設路徑；明確指定的參數一律優先。
