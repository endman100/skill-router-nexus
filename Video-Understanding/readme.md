# Video Understanding

此分類涵蓋長短影片的視覺內容理解、時間分段、影片問答、事件與鏡頭定位、電影語言分析、場景檢索及即時串流理解。適用於需要從影片畫面取得可驗證描述、時間戳摘要、運鏡與構圖證據、語意索引或事件警報的場景；純語音轉錄、剪輯、轉碼與影片生成應分別路由至其專屬分類。

## 核心 Skills

- `long-video-understand`：使用 VideoChat3 對長短影片進行可續跑的時間分段理解、問答與階層摘要。
- `filmops-first-video-analysis`：分析景別、構圖、鏡位、色調、人物站位與運鏡，產出電影語言證據。

## 跨分類相關 Skills

以下 Skills 保留在主要功能分類，避免新增第三份實作副本；遇到相應需求時應一併納入路由候選：

- [`videodb`](../Video-Editing/videodb/)：影片場景索引、時間戳檢索、RTSP 即時理解與事件警報，同時也提供剪輯與轉碼能力。
- [`wemm-embedding`](../AI-Research/wemm-embedding/)：影片 embedding、多模態語意檢索與 RAG。
- [`rn-motion-replica`](../Video-Editing/rn-motion-replica/)：拆解參考影片的布局、動作、節奏、轉場與時間結構，主要用於動效復刻。
- [`rn-replica-qc`](../Agent-Verification/rn-replica-qc/)：參考影片逐幀比較、時間對齊與交付驗證。

## 分類邊界

- 語音轉文字、字幕生成：`Speech-Recognition/`
- 下載、抽幀、裁切、轉碼與後製：`Video-Editing/`
- AI 影片生成、動畫與合成：`Video-Generation/` 或 `Creative-Video-Generation/`
- 視覺語言模型訓練、量化與推論框架研究：`AI-Research/`
