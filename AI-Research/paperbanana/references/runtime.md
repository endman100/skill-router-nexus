# 官方後端與來源

查閱日期：2026-09-09。已檢查原始碼版本：836455537e863b5a2f40dace487a782c0bc5ef94。

- [原作者專案](https://github.com/dwzhu-pku/PaperBanana)
- [上游技能](https://github.com/dwzhu-pku/PaperBanana/blob/836455537e863b5a2f40dace487a782c0bc5ef94/skill/SKILL.md)
- [上游 CLI](https://github.com/dwzhu-pku/PaperBanana/blob/836455537e863b5a2f40dace487a782c0bc5ef94/skill/run.py)
- [論文](https://arxiv.org/abs/2601.23265)
- [研究首頁與失敗案例](https://dwzhu-pku.github.io/PaperBanana/)
- [使用者最初提供的獨立平台](https://paper-banana.org/tw)

本封裝的指令與 wrapper 為原創整合，不複製上游實作。上游 repo 程式碼採 Apache-2.0，保留其授權。上游 skill frontmatter 另標示 MIT-0，不將其套用至整個 repo。

## Windows 設定

先找已有 checkout、git、uv 與專案虛擬環境。沿用使用者指定目錄；沒有時用當前工作區 work/PaperBanana，不要把執行環境或金鑰寫進技能資料夾。不修改或重設使用者既有 checkout。

新建 checkout 可按下列命令操作，把 <workspace> 替換為實際絕對路徑：

```powershell
git clone https://github.com/dwzhu-pku/PaperBanana.git '<workspace>/work/PaperBanana'
git -C '<workspace>/work/PaperBanana' checkout --detach 836455537e863b5a2f40dace487a782c0bc5ef94
uv venv --python 3.12 '<workspace>/work/PaperBanana/.venv'
uv pip install --python '<workspace>/work/PaperBanana/.venv/Scripts/python.exe' -r '<workspace>/work/PaperBanana/requirements.txt'
```

若 uv 不存在，可用可用的 Python 3.12 建立 venv 並用其 python -m pip install -r 安裝。套件未完全鎖版，因此 pin repo 不是完整環境重現保證。更新 repo 後重新檢查 CLI 參數、設定與輸出命名。

提供 OPENROUTER_API_KEY 或 GOOGLE_API_KEY 環境變數，或設定本地 configs/model_config.yaml。已有 key 時直接沿用；只檢查存在性，不輸出值、不寫入 prompt、日誌、技能或交付包。缺少金鑰時請使用者在本地設定，無須把值貼到對話。

YAML 可從 repo 的 configs/model_config.template.yaml 複製，已有設定不可覆蓋。模型名稱從設定讀取或 wrapper 參數覆蓋。預檢只確認非空 key／可匯入套件，無法保證額度、模型權限或 API 可達性。

wrapper 使用 <repo>/.venv/Scripts/python.exe（Windows）或 .venv/bin/python；其他環境請傳入 --python 的實際執行檔路徑。wrapper 在 repo 根目錄啟動 skill/run.py，以絕對路徑傳入文字與 PNG。

## 已確認的上游行為

- CLI 讀取 UTF-8 文字、圖說及參數；多候選輸出 figure_0.png 等。
- 無結果會非零退出，但有結果且全無圖片可能以零退出；wrapper 額外檢查所有預期 PNG。
- 輸出格式強制 PNG，因此 wrapper 只接受 .png。
- 上游圖片擷取只查 critic round 3 到 0，因此 wrapper 限制最多三輪。
- 上游自動下載資料，環境需要網路及磁碟空間；失敗時保留錯誤，不盲目重跑模型請求。
- plot 尚不能據此入口保證可用，本 wrapper 固定使用 diagram。
