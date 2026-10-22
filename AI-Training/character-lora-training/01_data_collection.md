# 01. 資料收集

輸入作品名 + 角色名，Codex 與 Grok Bot 同時用同一句指令各自收集，各存一個資料夾：

```
幫我收集 <作品名> <角色名> 可以用來訓練 LoRA 的資料
```

## Codex

```
python3 scripts/codex_collect.py "<作品名> <角色名>" <收集資料夾>
```

一次隔離 `codex exec`（可上網、只寫工作目錄），結果複製到 `<收集資料夾>/codex/`，含 `sources.json`（檔名與來源網址）。預設 `--model gpt-6.1-sol --effort high --timeout 3600`。同一資料夾不可重跑（不覆寫），重跑請換資料夾。

## Grok Bot

Grok Bot 同時用同一句指令自己收集，存到 `<收集資料夾>/grok/`，同樣寫 `sources.json`。
