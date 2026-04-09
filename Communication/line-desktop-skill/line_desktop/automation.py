"""
LINE Desktop GUI 自動化模組 (Windows)

透過 pyautogui / pygetwindow / pyperclip 控制 LINE Desktop，
取代原始 Node.js 版本中的 AutoHotkey 腳本。
"""

import time
import subprocess
import ctypes
import ctypes.wintypes

import pyautogui
import pyperclip
import pygetwindow as gw
import psutil


# 安全設定：關閉 pyautogui 的 failsafe 延遲但保留 failsafe
pyautogui.PAUSE = 0.05


class LineDesktopAutomation:
    """透過 GUI 操控 Windows 上的 LINE Desktop 應用程式。"""

    LINE_WINDOW_TITLE = "LINE"

    # 延遲常數 (秒)
    DELAY_SHORT = 0.2
    DELAY_MID = 0.6
    DELAY_MID_LONG = 1.2
    DELAY_LONG = 3.0

    # ── 視窗管理 ──────────────────────────────────────────

    @staticmethod
    def _get_dpi_scale() -> float:
        """取得主螢幕 DPI 縮放比例。"""
        try:
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            dpi = user32.GetDpiForSystem()
            return dpi / 96.0
        except Exception:
            return 1.0

    def _find_line_window(self):
        """找到 LINE Desktop 視窗，回傳 pygetwindow.Win32Window 或 None。"""
        windows = gw.getWindowsWithTitle(self.LINE_WINDOW_TITLE)
        for w in windows:
            # 排除「LINE - 」開頭的子視窗（如設定視窗），但保留主視窗
            if w.title == self.LINE_WINDOW_TITLE or w.title.startswith(self.LINE_WINDOW_TITLE):
                return w
        return None

    # ── 公開 Tool 方法 ─────────────────────────────────────

    def is_line_running(self) -> bool:
        """檢查 LINE Desktop 程序是否正在執行。"""
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == "line.exe":
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def activate_line(self) -> dict:
        """將 LINE Desktop 視窗帶到前景。"""
        win = self._find_line_window()
        if win is None:
            return {"success": False, "error": "找不到 LINE Desktop 視窗"}
        try:
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(self.DELAY_SHORT)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def select_chat(self, chat_name: str) -> bool:
        """在 LINE Desktop 中搜尋並選取指定的聊天室。"""
        win = self._find_line_window()
        if win is None:
            return False

        scale = self._get_dpi_scale()

        try:
            # 確保視窗在前景
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(self.DELAY_SHORT)

            # 點擊左側區域確保焦點在聊天列表
            click_x = win.left + int(30 * scale)
            click_y = win.top + int(110 * scale)
            pyautogui.click(click_x, click_y)
            time.sleep(self.DELAY_MID)

            # Ctrl+Shift+F 聚焦搜尋欄
            pyautogui.hotkey("ctrl", "shift", "f")
            time.sleep(self.DELAY_SHORT)

            # 清空搜尋欄並輸入聊天室名稱
            pyperclip.copy(chat_name)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("delete")
            time.sleep(self.DELAY_SHORT)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(self.DELAY_MID)

            # 按 Enter 搜尋，再點擊結果
            pyautogui.press("enter")
            time.sleep(self.DELAY_SHORT)

            click_x = win.left + int(200 * scale)
            click_y = win.top + int(140 * scale)
            pyautogui.click(click_x, click_y)
            time.sleep(self.DELAY_MID)

            return True
        except Exception as e:
            print(f"[ERROR] select_chat failed: {e}")
            return False

    def copy_all_chat_to_clipboard(self) -> str | None:
        """複製目前聊天室的所有訊息到剪貼簿。"""
        win = self._find_line_window()
        if win is None:
            return None

        scale = self._get_dpi_scale()

        try:
            win.activate()
            time.sleep(self.DELAY_SHORT)

            # 點擊聊天區域右側
            click_x = win.left + win.width - int(20 * scale)
            click_y = win.top + win.height // 2
            pyautogui.click(click_x, click_y)
            time.sleep(self.DELAY_SHORT)

            # Ctrl+A 全選, Ctrl+C 複製
            pyautogui.hotkey("ctrl", "a")
            time.sleep(self.DELAY_MID)
            pyperclip.copy("")  # 清空剪貼簿
            pyautogui.hotkey("ctrl", "c")
            time.sleep(self.DELAY_MID)

            result = pyperclip.paste()
            if not result:
                return None
            return result
        except Exception as e:
            print(f"[ERROR] copy_all_chat_to_clipboard failed: {e}")
            return None

    def page_up(self, times: int = 2) -> None:
        """在聊天室中向上捲動指定次數。"""
        win = self._find_line_window()
        if win is None:
            return

        scale = self._get_dpi_scale()

        try:
            win.activate()
            time.sleep(self.DELAY_SHORT)

            # 點擊聊天區域
            click_x = win.left + int(400 * scale)
            click_y = win.top + win.height - int(100 * scale)
            pyautogui.click(click_x, click_y)
            time.sleep(self.DELAY_SHORT)

            pyautogui.press("tab")
            time.sleep(self.DELAY_SHORT)
            pyautogui.press("end")
            time.sleep(self.DELAY_SHORT)

            for _ in range(times):
                pyautogui.press("pageup")
                time.sleep(self.DELAY_SHORT)
        except Exception as e:
            print(f"[ERROR] page_up failed: {e}")

    def send_message(self, chat_name: str, message: str, auto_send: bool = True) -> dict:
        """
        在聊天室中輸入訊息。

        Args:
            chat_name: 聊天室名稱
            message: 訊息內容（支援多行）
            auto_send: True 時自動按 Enter 送出，False 時僅填入不送出
        """
        win = self._find_line_window()
        if win is None:
            return {"success": False, "error": "找不到 LINE Desktop 視窗"}

        scale = self._get_dpi_scale()

        try:
            win.activate()
            time.sleep(self.DELAY_SHORT)

            # 點擊輸入框區域
            click_x = win.left + int(win.width * 3 / 4)
            click_y = win.top + win.height - int(100 * scale)
            pyautogui.click(click_x, click_y)
            time.sleep(self.DELAY_SHORT)

            # 清空輸入框
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("delete")
            time.sleep(self.DELAY_LONG)

            # 依行送入訊息
            lines = message.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            for i, line in enumerate(lines):
                if line:
                    pyperclip.copy(line)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(self.DELAY_SHORT)
                if i < len(lines) - 1:
                    # Shift+Enter 換行
                    pyautogui.hotkey("shift", "enter")
                    time.sleep(self.DELAY_SHORT)

            if auto_send:
                pyautogui.press("enter")
                time.sleep(self.DELAY_SHORT)

            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── 組合 Tool 方法 ─────────────────────────────────────

    def get_chat_history(
        self,
        chat_name: str,
        date: str | None = None,
        message_limit: int = 100,
        page_up_times: int = 10,
    ) -> str:
        """
        讀取指定聊天室的歷史訊息。

        Args:
            chat_name: 聊天室/群組名稱
            date: 日期 (YYYY-MM-DD)，預設今天
            message_limit: 最大訊息數
            page_up_times: 向上捲動次數（控制讀取範圍）

        Returns:
            聊天歷史文字
        """
        result = self.activate_line()
        if not result["success"]:
            raise RuntimeError(f"無法啟動 LINE Desktop: {result.get('error')}")

        ok = self.select_chat(chat_name)
        if not ok:
            raise RuntimeError(f'找不到聊天室 "{chat_name}"')

        self.page_up(page_up_times)

        history = self.copy_all_chat_to_clipboard()
        if history is None:
            return ""

        # 限制回應長度（從尾部截取）
        return history[-50000:]

    def send_chat_message(
        self,
        chat_name: str,
        message: str,
        auto_send: bool = False,
    ) -> dict:
        """
        在指定聊天室發送訊息。

        Args:
            chat_name: 聊天室/群組名稱
            message: 訊息內容
            auto_send: 是否自動送出

        Returns:
            {"success": bool, "error": str|None}
        """
        result = self.activate_line()
        if not result["success"]:
            return {"success": False, "error": f"無法啟動 LINE Desktop: {result.get('error')}"}

        ok = self.select_chat(chat_name)
        if not ok:
            return {"success": False, "error": f'找不到聊天室 "{chat_name}"'}

        return self.send_message(chat_name, message, auto_send)
