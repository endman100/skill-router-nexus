---
name: skill-MegaDownloader
description: >
  Download and decrypt files from MEGA.nz without relying on the mega.py library.
  Use when the user wants to download a MEGA file link (mega.nz/file/... or mega.nz/#!...).
  Handles key derivation, AES-CTR decryption, and progress display automatically.
  Triggers on: "download from mega", "mega link", "mega.nz", "mega downloader".
  Script location: d:\skill-MegaDownloader\mega_downloader.py
---

# MegaDownloader Skill

純 Python 實作的 MEGA.nz 單一檔案下載器，不依賴 mega.py。
完整 script 位於：`d:\skill-MegaDownloader\mega_downloader.py`

## 依賴安裝

```bash
pip install requests cryptography tqdm
```

## 使用方式

```bash
# 基本下載（輸出至 ./download/）
python mega_downloader.py "https://mega.nz/file/FILE_ID#KEY"

# 指定輸出資料夾
python mega_downloader.py "https://mega.nz/file/FILE_ID#KEY" -o /path/to/dir

# 自動覆蓋已存在檔案（不詢問）
python mega_downloader.py "https://mega.nz/file/FILE_ID#KEY" -y
```

## 支援連結格式

| 格式 | 範例 |
|------|------|
| 新格式 | `https://mega.nz/file/FILE_ID#KEY` |
| 舊格式 | `https://mega.nz/#!FILE_ID!KEY` |

## 工作流程

1. 解析連結取得 `file_id` 與 `key_b64`
2. 以 XOR 推導 AES-128 key 與 8-byte nonce（IV）
3. 呼叫 `https://g.api.mega.co.nz/cs` 取得下載 URL 與加密屬性
4. 以 CBC 解密屬性（檔名）
5. 串流下載加密檔案至暫存路徑
6. 以 AES-128-CTR 解密並輸出最終檔案
7. 自動清除暫存加密檔

## 已知 MEGA 錯誤碼

| 碼 | 說明 |
|----|------|
| -2 | 檔案不存在或已被刪除 |
| -4 | 被 MEGA 管理員移除 |
| -6 | 下載額度用盡（稍後再試或換 IP） |
| -9 | 連結無效 |
