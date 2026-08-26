# 逆向分析 / Reverse Analysis

此分類統一收納逆向分析與 CTF 競賽分析 skill，涵蓋二進位、行動應用、前端 JavaScript、惡意程式、數位鑑識、雲端、身分、協定、硬體、漏洞利用與多類型 CTF 題目。所有 skill 均以單層目錄攤平，適用於需要直接搜尋、載入或組合逆向與競賽分析工作流的場景。

本分類的每個直接子資料夾都是可由 `skill_reader.py` 掃描的完整 skill 資料夾；核心與 CTF skill 均直接攤平在此層，不使用薄包裝或隱藏的 `.canonical` 跳轉層。`reverse-skill-router/` 僅保留總控入口與共用資源，內部重複的 `SKILL.md` 已移除；路由結果會指向本分類的同層 skill。其餘 skill 依專案規範複製完整目錄，並可同時保留在其他相關功能分類中。
