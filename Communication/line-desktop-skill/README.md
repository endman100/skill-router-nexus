# LINE Desktop Skill (Python)

透過 GUI 自動化操控 **LINE Desktop** 應用程式（Windows），讓 AI Agent 能讀取聊天訊息、發送訊息。

> ⚠️ 本專案與 LINE 官方無任何關聯。無需 LINE Developers 帳號或 Channel Access Token。

---

## 功能

- 📖 讀取 LINE 聊天室/群組歷史訊息
- ✉️ 發送訊息（手動確認 或 自動送出）
- 🔍 搜尋並選取聊天室
- 🤖 可整合至任何 AI Agent / Copilot Skill 工作流程

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
pip install -r requirements.txt
```

依賴套件：`pyautogui`、`pyperclip`、`pygetwindow`、`psutil`、`Pillow`

---

# 使用方式（CLI）

```bash
# 檢查 LINE 是否執行中
python {SKILL_PATH}\line_desktop is_line_running

# 讀取聊天室歷史訊息（一般）
python {SKILL_PATH}\line_desktop get_chat_history --chat_name "專案討論"

# 讀取最近幾筆（快速）
python {SKILL_PATH}\line_desktop get_chat_history --chat_name "專案討論" --mode short

# 讀取完整歷史（適合摘要分析）
python {SKILL_PATH}\line_desktop get_chat_history --chat_name "專案討論" --mode long

# 傳入訊息（直接送出）
python {SKILL_PATH}\line_desktop send_message --chat_name "專案討論" --message "Hello!"

# 選取聊天室
python {SKILL_PATH}\line_desktop select_chat --chat_name "專案討論"
```

---

## 工具清單

| Tool | 說明 |
|------|------|
| `is_line_running` | 檢查 LINE Desktop 是否執行中 |
| `activate_line` | 將 LINE 視窗帶到前景 |
| `get_chat_history` | 讀取聊天歷史（short / default / long） |
| `send_message` | 發送訊息（預設直接送出） |
| `select_chat` | 搜尋並選取聊天室 |

與原版 MCP 對照：

| 原始 MCP tool | 本 Skill |
|--------------|---------|
| `get_line_chatroom_history_short` | `get_chat_history --mode short` |
| `get_line_chatroom_history_default` | `get_chat_history --mode default` |
| `get_line_chatroom_history_long` | `get_chat_history --mode long` |
| `send_message_manual` | `send_message --no_auto_send`（手動確認） |
| `send_message_auto` | `send_message`（預設） |

---

## 專案結構

```
line-desktop-skill/
├── README.md
├── SKILL.md                    ← Skill 說明（供 Agent 使用）
├── requirements.txt
└── line_desktop/
    ├── __init__.py
    ├── __main__.py             ← python {SKILL_PATH}\\line_desktop 入口
    ├── cli.py                  ← CLI 介面
    ├── automation.py           ← GUI 自動化核心（pyautogui + pygetwindow）
    └── tools.py                ← Tool 函式集
```

---

## 使用注意事項

1. **執行期間請勿操作滑鼠** — GUI 自動化過程中滑鼠移動會干擾執行。
2. **展開聊天視窗模式** — LINE Desktop 須設定為聊天視窗固定在右側的模式。
3. **主螢幕** — 多螢幕環境下，LINE Desktop 須放在主螢幕。
4. **DPI** — 已自動偵測 DPI 縮放比例，支援高 DPI 螢幕。

---

## License

MIT
