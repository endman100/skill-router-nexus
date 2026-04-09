#!/usr/bin/env python3
"""
LINE Desktop Skill — CLI 入口

用法:
    python {SKILL_PATH}\\line_desktop <tool_name> [--arg value ...]

範例:
    python {SKILL_PATH}\\line_desktop is_line_running
    python {SKILL_PATH}\\line_desktop get_chat_history --chat_name "專案討論"
    python {SKILL_PATH}\\line_desktop get_chat_history --chat_name "專案討論" --mode long
    python {SKILL_PATH}\\line_desktop send_message --chat_name "專案討論" --message "Hello!"
    python {SKILL_PATH}\\line_desktop select_chat --chat_name "專案討論"
    python {SKILL_PATH}\\line_desktop activate_line
"""

import argparse
import sys

from line_desktop.tools import (
    is_line_running,
    activate_line,
    get_chat_history,
    send_message,
    select_chat,
)


def main():
    parser = argparse.ArgumentParser(
        description="LINE Desktop Skill CLI",
    )
    sub = parser.add_subparsers(dest="tool", help="要執行的工具名稱")

    # is_line_running
    sub.add_parser("is_line_running", help="檢查 LINE Desktop 是否執行中")

    # activate_line
    sub.add_parser("activate_line", help="將 LINE Desktop 帶到前景")

    # get_chat_history
    p_hist = sub.add_parser("get_chat_history", help="讀取聊天室歷史訊息")
    p_hist.add_argument("--chat_name", required=True, help="聊天室/群組名稱")
    p_hist.add_argument("--mode", default="default", choices=["short", "default", "long"])
    p_hist.add_argument("--date", default=None, help="日期 YYYY-MM-DD")
    p_hist.add_argument("--message_limit", type=int, default=100)

    # send_message
    p_send = sub.add_parser("send_message", help="在聊天室中發送訊息（預設直接送出）")
    p_send.add_argument("--chat_name", required=True, help="聊天室/群組名稱")
    p_send.add_argument("--message", required=True, help="訊息內容")
    p_send.add_argument("--no_auto_send", action="store_true", help="不自動送出，只填入")

    # select_chat
    p_sel = sub.add_parser("select_chat", help="搜尋並選取聊天室")
    p_sel.add_argument("--chat_name", required=True, help="聊天室/群組名稱")

    args = parser.parse_args()

    if not args.tool:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "is_line_running": lambda a: is_line_running(),
        "activate_line": lambda a: activate_line(),
        "get_chat_history": lambda a: get_chat_history(
            chat_name=a.chat_name, mode=a.mode, date=a.date, message_limit=a.message_limit
        ),
        "send_message": lambda a: send_message(
            chat_name=a.chat_name, message=a.message, auto_send=not a.no_auto_send
        ),
        "select_chat": lambda a: select_chat(chat_name=a.chat_name),
    }

    result = dispatch[args.tool](args)
    print(result)


if __name__ == "__main__":
    main()
