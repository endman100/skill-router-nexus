---
name: comfyui-python-ws-client
description: Python WebSocket client patterns for ComfyUI. Covers websocket-client connection lifecycle, client_id management, real-time execution monitoring, timeout handling, and common Python pitfalls (mutable defaults, __del__ vs __delattr__). Use when writing or debugging Python code that connects to ComfyUI via WebSocket.
metadata:
  {
    "openclaw":
      {
        "emoji": "🐍",
        "os": ["darwin", "linux", "win32"],
        "requires": { "pip": ["websocket-client", "requests"] },
      },
  }
---

# ComfyUI Python WebSocket Client

使用 Python `websocket-client` 連接 ComfyUI WebSocket 進行即時執行監控、佇列送出與結果擷取的完整知識。

---

## 核心架構

```
Python Client                     ComfyUI Server
─────────────                     ──────────────
1. ws.connect(ws://.../ws?clientId=UUID)  ──►  註冊 client
2. POST /prompt {prompt, client_id}       ──►  加入 queue
3. ws.recv() loop                         ◄──  即時推送 executing/progress/preview
4. GET /history/{prompt_id}               ──►  取得最終結果
5. GET /view?filename=...                 ──►  下載圖片
```

---

## 連線建立模式

### 正確寫法

```python
import websocket
import uuid

class WorkflowAPI:
    def __init__(self, server_address, client_id=None):
        if client_id is None:
            client_id = str(uuid.uuid4())  # 每次實例化產生新 UUID
        self.client_id = client_id
        self.server_address = server_address
        self.ws = websocket.WebSocket()
        self.ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
        self.ws.settimeout(5)

    def __del__(self):
        try:
            self.ws.close()
        except Exception:
            pass
```

### ⚠️ 陷阱 1：Python Mutable Default Argument

```python
# ❌ 錯誤 — uuid.uuid4() 在 class 定義時只執行一次，所有實例共用同一 UUID
def __init__(self, server_address, client_id=str(uuid.uuid4())):

# ✅ 正確 — 使用 None sentinel，在 __init__ 內部生成
def __init__(self, server_address, client_id=None):
    if client_id is None:
        client_id = str(uuid.uuid4())
```

**原理**：Python 的 default argument 在函式定義時（即 class 載入時）求值一次並存入 `__defaults__`，後續呼叫不會重新求值。這是 Python 最經典的陷阱之一。

**後果**：所有 `WorkflowAPI` 實例使用相同 `client_id` 連 ComfyUI，ComfyUI 對同一 `client_id` 的多條 WebSocket 連線行為不確定，可能把完成通知送到錯誤的連線，導致 `wait_queue_end` 永遠收不到完成訊號而 timeout。

---

### ⚠️ 陷阱 2：`__del__` vs `__delattr__`

```python
# ❌ 錯誤 — __delattr__ 是「刪除屬性」時觸發，幾乎不會被呼叫
def __delattr__(self, __name: str) -> None:
    self.ws.close()

# ✅ 正確 — __del__ 是物件被 GC 回收時觸發
def __del__(self):
    self.ws.close()
```

| 方法 | 觸發時機 | 實際用途 |
|------|---------|---------|
| `__del__(self)` | 物件被垃圾回收時（reference count 歸零） | 資源清理 (finalizer) |
| `__delattr__(self, name)` | `del obj.attribute` 刪除屬性時 | 自定義屬性刪除行為 |

**後果**：WebSocket 連線永遠不會被主動關閉，舊連線持續存活。配合陷阱 1，ComfyUI 對同一 `client_id` 堆積多條殭屍連線，訊息分發混亂。

---

## client_id 的重要性

ComfyUI 使用 `client_id` 來路由 WebSocket 訊息：

- **每個 client_id 應對應唯一的 WebSocket 連線**
- ComfyUI 只會把該 client 送出的 prompt 執行訊息推送給對應的 WebSocket
- 若多個連線使用同一 `client_id`，行為未定義（可能只送到第一條、最後一條、或隨機）
- **最佳實踐**：每次建立新的 `WorkflowAPI` 實例時，確保舊連線已關閉，並使用新的 UUID

---

## WebSocket 訊息協議

ComfyUI 透過 WebSocket 推送以下訊息類型：

### 文字訊息（JSON）

```json
{"type": "status", "data": {"status": {"exec_info": {"queue_remaining": 1}}}}
{"type": "execution_start", "data": {"prompt_id": "abc-123"}}
{"type": "executing", "data": {"node": "3", "prompt_id": "abc-123"}}
{"type": "progress", "data": {"value": 5, "max": 20, "prompt_id": "abc-123"}}
{"type": "executing", "data": {"node": null, "prompt_id": "abc-123"}}  ← 完成
{"type": "execution_cached", "data": {"nodes": ["1","2"], "prompt_id": "abc-123"}}
```

### 二進位訊息

- Preview 圖片（進度預覽）以 binary data 推送
- 需用 `isinstance(out, str)` 判斷是否為 JSON

### 完成判定

```python
if message['type'] == 'executing':
    data = message['data']
    if data['node'] is None and data['prompt_id'] == workflow_id:
        # workflow 已完成
        break
```

**`node: null`** 表示所有節點執行完畢。必須同時比對 `prompt_id`，因為可能有其他 client 的任務訊息混入。

---

## Timeout 處理策略

### socket-level timeout + 累計 timeout

```python
def wait_queue_end(self, workflow_id, max_timeout=360):
    total_timeout = 0
    while True:
        try:
            out = self.ws.recv()
        except websocket._exceptions.WebSocketTimeoutException:
            total_timeout += self.ws.gettimeout() or 5
            if total_timeout > max_timeout:
                raise TimeoutError(f"wait_queue_end timeout {max_timeout} sec")
            continue
        except Exception as e:
            raise

        total_timeout = 0  # 收到任何訊息就重置 timeout 計數器

        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == workflow_id:
                    break
```

**注意**：`total_timeout` 在每次成功收到訊息後重置為 0。這表示 timeout 是「連續無訊息」的累計時間，而非「總執行時間」，對長時間生成（如影片）更友善。

---

## 常見 Timeout 排查清單

| 症狀 | 可能原因 | 排查方式 |
|------|---------|---------|
| 持續 `ws time out 5 sec, re recv` 到 360s | client_id 重複 / 舊連線未關閉 | 確認每次實例化用新 UUID，舊實例已 `ws.close()` |
| 圖片已生成但 WS 收不到完成訊號 | 完成通知送到其他連線 | 檢查是否有多個連線使用相同 client_id |
| 偶發 timeout | ComfyUI 內部錯誤未回傳 | 檢查 ComfyUI server log，嘗試 `GET /history/{id}` 確認狀態 |
| 首次正常、後續 timeout | `__del__` 未實作或用錯 `__delattr__` | 確保前一個連線正確關閉 |

---

## REST API 操作速查

### 送出 Workflow

```python
import urllib.request, json

def queue_workflow(self, workflow):
    payload = {"prompt": workflow, "client_id": self.client_id}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"http://{self.server_address}/prompt", data=data
    )
    return json.loads(urllib.request.urlopen(req).read())
```

回傳 `{"prompt_id": "...", "number": N}`。

### 查詢歷史

```python
def get_history(self, prompt_id):
    url = f"http://{self.server_address}/history/{prompt_id}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())
```

### 下載圖片

```python
def get_image(self, filename, subfolder, folder_type):
    params = urllib.parse.urlencode({
        "filename": filename, "subfolder": subfolder, "type": folder_type
    })
    url = f"http://{self.server_address}/view?{params}"
    with urllib.request.urlopen(url) as resp:
        return resp.read()
```

### 上傳圖片

```python
import requests

def upload_image(self, filepath, subfolder):
    url = f"http://{self.server_address}/upload/image"
    with open(filepath, 'rb') as f:
        files = {'image': f}
        data = {'overwrite': 'true', 'subfolder': subfolder}
        requests.post(url, files=files, data=data)
```

---

## 完整範例：Benchmark 用法

```python
import time, random

def run_once(workflow_path, host="127.0.0.1", port="8188"):
    workflow = load_workflow(workflow_path)
    # 修改 seed 確保不命中快取
    workflow[sampler_id]["inputs"]["seed"] += random.randint(1, 1000000)

    api = WorkflowAPI(f"{host}:{port}")  # 每次新 UUID + 新連線
    try:
        start = time.perf_counter()
        prompt_id = api.queue_workflow(workflow)["prompt_id"]
        api.wait_queue_end(prompt_id)
        return time.perf_counter() - start
    finally:
        api.ws.close()  # 顯式關閉，不依賴 __del__
```

**要點**：
- 每次 `run_once` 建立新的 `WorkflowAPI`，避免連線重用問題
- 用 `try/finally` 確保 WS 關閉，比依賴 `__del__` 更可靠
- 修改 `seed` 避免 ComfyUI 快取跳過計算

---

## Python 知識點總結

| 知識點 | 重要性 | 說明 |
|--------|--------|------|
| Mutable Default Argument | 🔴 Critical | `def f(x=[])` 或 `def f(x=uuid4())` — default 只在定義時求值一次 |
| `__del__` vs `__delattr__` | 🔴 Critical | finalizer vs 屬性刪除攔截，用途完全不同 |
| WebSocket 資源管理 | 🟡 Important | 未關閉的 WS 連線會導致伺服器端資源洩漏與訊息路由錯誤 |
| `settimeout` 行為 | 🟡 Important | socket timeout 會讓 `recv()` 拋出 `WebSocketTimeoutException`，需在迴圈中處理 |
| `isinstance` 判斷訊息類型 | 🟢 Normal | 區分 JSON 文字訊息與 binary preview 資料 |
| `client_id` 唯一性 | 🔴 Critical | ComfyUI 用 client_id 路由訊息，重複會導致訊息丟失 |
