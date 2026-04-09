"""
LINE Desktop Skill — Tool 函式集

供 Agent / Copilot Skill 直接呼叫的工具函式，
每個函式對應原始 MCP 版本的一個 tool。
"""

import json
from datetime import datetime, timezone

from line_desktop.automation import LineDesktopAutomation

_auto = LineDesktopAutomation()


# ────────────────────────────────────────────────
# Tool 1: is_line_running
# ────────────────────────────────────────────────
def is_line_running() -> str:
    """
    檢查 LINE Desktop 是否正在執行。

    Returns:
        JSON 字串 {"running": bool}
    """
    running = _auto.is_line_running()
    return json.dumps({"running": running}, ensure_ascii=False)


# ────────────────────────────────────────────────
# Tool 2: activate_line
# ────────────────────────────────────────────────
def activate_line() -> str:
    """
    將 LINE Desktop 視窗帶到前景。

    Returns:
        JSON 字串 {"success": bool, "error": str|null}
    """
    result = _auto.activate_line()
    return json.dumps(result, ensure_ascii=False)


# ────────────────────────────────────────────────
# Tool 3: get_chat_history
# ────────────────────────────────────────────────
def get_chat_history(
    chat_name: str,
    mode: str = "default",
    date: str | None = None,
    message_limit: int = 100,
) -> str:
    """
    讀取指定 LINE 聊天室的歷史訊息。

    Args:
        chat_name:     聊天室/群組名稱（必填）
        mode:          讀取模式
                       - "short"   — 最近幾筆（page_up=5），快速回覆
                       - "default" — 一般讀取（page_up=10）
                       - "long"    — 完整讀取（page_up=50），適合摘要分析
        date:          日期 (YYYY-MM-DD)，預設今天
        message_limit: 最大訊息數，預設 100

    Returns:
        JSON 字串，包含 chatName, date, messageLimit, history, chatRoomUpdatedAt
    """
    page_up_map = {"short": 5, "default": 10, "long": 50}
    page_up_times = page_up_map.get(mode, 10)

    target_date = date or datetime.now().strftime("%Y-%m-%d")

    try:
        history = _auto.get_chat_history(
            chat_name=chat_name,
            date=target_date,
            message_limit=message_limit,
            page_up_times=page_up_times,
        )
    except RuntimeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    return json.dumps(
        {
            "chatName": chat_name,
            "date": target_date,
            "messageLimit": message_limit,
            "mode": mode,
            "history": history,
            "chatRoomUpdatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        ensure_ascii=False,
    )


# ────────────────────────────────────────────────
# Tool 4: send_message
# ────────────────────────────────────────────────
def send_message(
    chat_name: str,
    message: str,
    auto_send: bool = True,
) -> str:
    """
    在指定 LINE 聊天室中發送訊息（預設直接送出）。

    Args:
        chat_name: 聊天室/群組名稱（必填）
        message:   訊息內容（必填，支援多行）
        auto_send: True  → 自動按 Enter 送出（預設）
                   False → 僅填入訊息，等使用者手動確認

    Returns:
        JSON 字串 {"success": bool, "chatName": str, "message": str,
                    "timestamp": str, "error": str|null}
    """
    result = _auto.send_chat_message(
        chat_name=chat_name,
        message=message,
        auto_send=auto_send,
    )

    return json.dumps(
        {
            "success": result["success"],
            "chatName": chat_name,
            "message": message,
            "autoSend": auto_send,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": result.get("error"),
        },
        ensure_ascii=False,
    )


# ────────────────────────────────────────────────
# Tool 5: select_chat
# ────────────────────────────────────────────────
def select_chat(chat_name: str) -> str:
    """
    搜尋並選取指定的 LINE 聊天室（不讀取訊息、不發送）。

    Args:
        chat_name: 聊天室/群組名稱（必填）

    Returns:
        JSON 字串 {"success": bool, "chatName": str}
    """
    _auto.activate_line()
    ok = _auto.select_chat(chat_name)
    return json.dumps({"success": ok, "chatName": chat_name}, ensure_ascii=False)


# ────────────────────────────────────────────────
# 工具清單（供 SKILL.md 或 Agent 自動發現）
# ────────────────────────────────────────────────
TOOLS = {
    "is_line_running": is_line_running,
    "activate_line": activate_line,
    "get_chat_history": get_chat_history,
    "send_message": send_message,
    "select_chat": select_chat,
}
