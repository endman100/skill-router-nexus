---
name: line-desktop-skill
description: "透過 GUI 自動化操控 Windows 上的 LINE Desktop 應用程式。讀取聊天訊息、發送訊息、選取聊天室。Python 版本，無需 AutoHotkey 或 LINE Developers 帳號。Use when user asks to read LINE messages, send LINE messages, check LINE status, or interact with LINE Desktop."
---

# LINE Desktop Skill (Python)

> 透過 GUI 自動化操控 **LINE Desktop** 應用程式（Windows）。
> 本 Skill 是 [dtwang/line-desktop-mcp](https://github.com/dtwang/line-desktop-mcp) 的 **Python 重寫版本**，
> 以 `pyautogui` + `pygetwindow` + `pyperclip` 取代 AutoHotkey。

---

## ⚠️ 使用注意事項

- 透過**已登入的 LINE Desktop** 視窗進行 GUI 自動化操作。
- 自動化執行期間**請勿操作滑鼠**，以免干擾。
- LINE Desktop 須使用「展開聊天視窗」模式（聊天視窗固定在右側）。
- 多螢幕環境下，LINE Desktop 須放在**主螢幕**。
- DPI 縮放已自動偵測，支援高 DPI 螢幕。

---

## 系統需求

| 項目 | 版本 |
|------|------|
| LINE Desktop | v9.10+ |
| Windows | 10+ |
| Python | 3.11+ |

---

## 安裝

```bash
cd d:\line-desktop-skill
pip install -r requirements.txt
```

依賴套件：`pyautogui`, `pyperclip`, `pygetwindow`, `psutil`, `Pillow`

---

## 工具清單 (Tools)

本 Skill 提供 **5 個工具**，全部已完成實作：

### Tool 1: `is_line_running`

**功能**：檢查 LINE Desktop 程序是否正在執行。

**回傳**：`{"running": true/false}`

```bash
python {SKILL_PATH}\line_desktop is_line_running
```

---

### Tool 2: `activate_line`

**功能**：將 LINE Desktop 視窗帶到前景（如果最小化則還原）。

**回傳**：`{"success": true/false, "error": null/"錯誤訊息"}`

```bash
python {SKILL_PATH}\line_desktop activate_line
```

---

### Tool 3: `get_chat_history`

**功能**：讀取指定 LINE 聊天室的歷史訊息。

| 參數 | 型別 | 必填 | 預設 | 說明 |
|------|------|------|------|------|
| `--chat_name` | str | ✅ | — | 聊天室/群組名稱 |
| `--mode` | str | ❌ | `default` | `short` / `default` / `long` |
| `--date` | str | ❌ | 今天 | 日期 `YYYY-MM-DD` |
| `--message_limit` | int | ❌ | 100 | 最大訊息數 |

**回傳**：`{"chatName", "date", "messageLimit", "mode", "history", "chatRoomUpdatedAt"}`

| mode | 捲動次數 | 適用情境 |
|------|---------|---------|
| `short` | 5 | 快速回覆，只需最新幾筆 |
| `default` | 10 | 一般查詢 |
| `long` | 50 | 摘要/分析大量歷史訊息 |

```bash
python {SKILL_PATH}\line_desktop get_chat_history --chat_name "專案討論"
python {SKILL_PATH}\line_desktop get_chat_history --chat_name "專案討論" --mode long
python {SKILL_PATH}\line_desktop get_chat_history --chat_name "專案討論" --date 2026-04-01
```

---

### Tool 4: `get_recent_chats`

**功能**：讀取 LINE 聊天列表中最前面的 N 個聊天室名稱（透過 Windows UI Automation）。

| 參數 | 型別 | 必填 | 預設 | 說明 |
|------|------|------|------|------|
| `--n` | int | ❌ | 10 | 回傳數量上限 |

**回傳**：`{"chats": ["群組A", "好友B", ...], "count": N}`

```bash
python {SKILL_PATH}\line_desktop get_recent_chats
python {SKILL_PATH}\line_desktop get_recent_chats --n 20
```

---

### Tool 5: `list_contacts`

**功能**：切換至 LINE 好友/群組頁籤並列出聯絡人清單（透過 Windows UI Automation）。

| 參數 | 型別 | 必填 | 預設 | 說明 |
|------|------|------|------|------|
| `--contact_type` | str | ❌ | `all` | `all` / `friends` / `groups` |

**回傳**：`{"contacts": ["好友A", "群組B", ...], "count": N, "type": "all"}`

```bash
python {SKILL_PATH}\line_desktop list_contacts
python {SKILL_PATH}\line_desktop list_contacts --contact_type groups
python {SKILL_PATH}\line_desktop list_contacts --contact_type friends
```

---

### Tool 6: `send_message`

**功能**：在指定 LINE 聊天室中發送訊息。預設**直接送出**。

| 參數 | 型別 | 必填 | 預設 | 說明 |
|------|------|------|------|------|
| `--chat_name` | str | ✅ | — | 聊天室/群組名稱 |
| `--message` | str | ✅ | — | 訊息內容（支援 `\n` 多行） |
| `--no_auto_send` | flag | ❌ | — | 加上此旗標則僅填入，不送出 |

**回傳**：`{"success", "chatName", "message", "autoSend", "timestamp", "error"}`

```bash
# 直接送出（預設）
python {SKILL_PATH}\line_desktop send_message --chat_name "專案討論" --message "Hello!"
```

---

### Tool 5: `select_chat`

**功能**：搜尋並選取指定的 LINE 聊天室（不讀取也不發送）。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `--chat_name` | str | ✅ | 聊天室/群組名稱 |

**回傳**：`{"success": true/false, "chatName": "..."}`

```bash
python {SKILL_PATH}\line_desktop select_chat --chat_name "專案討論"
```

---

## 原始 MCP 版本 → 本 Skill 對照表

| 原始 MCP tool | 本 Skill 工具 | 說明 |
|--------------|--------------|------|
| `get_line_chatroom_history_default` | `get_chat_history --mode default` | 一般讀取 |
| `get_line_chatroom_history_long` | `get_chat_history --mode long` | 完整讀取 |
| `get_line_chatroom_history_short` | `get_chat_history --mode short` | 快速讀取 |
| `send_message_manual` | `send_message` | 手動確認 |
| `send_message_auto` | `send_message`（預設） | 自動送出 |
| _(無)_ | `is_line_running` | ✨ 新增 |
| _(無)_ | `activate_line` | ✨ 新增 |
| _(無)_ | `select_chat` | ✨ 新增 |

---

## 專案結構

```
d:\line-desktop-skill\
├── SKILL.md                    ← 本檔（Skill 說明文件）
├── requirements.txt            ← Python 依賴
└── line_desktop/
    ├── __init__.py
    ├── __main__.py             ← python {SKILL_PATH}\line_desktop 入口
    ├── cli.py                  ← CLI 命令列介面
    ├── automation.py           ← GUI 自動化核心（pyautogui + pygetwindow）
    └── tools.py                ← Tool 函式集（Agent 呼叫入口）
```


