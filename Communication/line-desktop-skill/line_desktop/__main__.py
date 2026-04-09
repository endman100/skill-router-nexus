import sys
import os

# 讓 `python line_desktop ...`（非 -m 模式）也能找到 line_desktop 套件
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from line_desktop.cli import main

main()
