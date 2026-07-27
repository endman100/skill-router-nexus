#!/usr/bin/env python3
"""Deprecated alias for the current Markdown validator.

This file no longer reads JSON or writes preview Markdown. It accepts the same
arguments as validate.py and delegates directly to that command.
"""

from validate import main


if __name__ == "__main__":
    print("[已棄用] to_preview_md.py 現在只轉交 Markdown 內容審核")
    raise SystemExit(main())
