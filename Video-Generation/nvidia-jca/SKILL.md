---
name: nvidia-jca
description: >-
  說明 NVIDIA JCA（Joints, Camera, Action!）如何用指定骨架同步生成影片與 3D 關節動作。
  使用者問到 JCA、骨架驅動動畫或影片、影片與骨架動作互轉，或想用 JCA 為既有 VRM 角色生成動作並沿用原蒙皮免重綁時使用。
---

# NVIDIA JCA（Joints, Camera, Action!）

JCA 為使用者提供的骨架同步生成影片與可重播的 3D 關節動作，並估計固定相機，以對齊動作與畫面。

**發布狀態**　截至 2026-11-18，官方程式碼與權重均未公開。若使用者要安裝或執行，先查官方專案頁的發布狀態。 [NVIDIA 專案頁](https://research.nvidia.com/labs/par/projects/jca/)

## 論文方法（arXiv 2610.28632）

- 將骨架表示為有向樹。圖網路編碼關節名稱、靜止姿勢、父子關係，以及參考圖上可用的 2D 關節位置。
- 動作 DiT 結合全域注意力與骨架圖注意力，直接生成逐幀關節旋轉與位置。影片分支以 Wan2.2 I2V-A14B 為基礎，兩分支在共同去噪時透過雙向交叉注意力交換特徵。
- 關節定位頭從影片預測 2D 關節位置，再與生成的 3D 關節配對，估計每段影片的靜態透視相機旋轉、平移與焦距。 [論文 §3](https://arxiv.org/pdf/2610.28632#page=4)

## 依使用者需求判讀輸入與輸出

- **文字生成**　輸入提示詞與靜止姿勢骨架，可加首幀參考圖與 2D 關節位置，輸出影片、3D 動作與相機估計。
- **關鍵影格控制**　在提示詞與骨架之外提供帶時間點的 RGB 關鍵影格，由模型補出中間的影片與動作。
- **影片轉動作**　輸入影片與靜止姿勢骨架，生成該骨架的 3D 動作。
- **動作轉影片**　輸入骨架、3D 動作和文字，可加首幀參考圖，生成對應影片。 [論文 §4.4–4.5](https://arxiv.org/pdf/2610.28632#page=9) · [附錄 D](https://arxiv.org/pdf/2610.28632#page=23)

若要評估場景互動，留意論文設定為每段一副骨架、固定相機。訓練資料偏向雙足，接觸正確性與避免穿模仍需逐段驗證。 [論文 §6](https://arxiv.org/pdf/2610.28632#page=10)

## VRM 角色免重綁（推測，待實測）

若 JCA 能依角色原骨架生成動作，將動畫寫回同一批 glTF 節點即可沿用原骨架、蒙皮權重與逆綁定矩陣。

JCA 的根旋轉與位置使用世界座標，其餘關節採父骨局部旋轉與相對根的位置。 [論文附錄 A.1–A.3](https://arxiv.org/pdf/2610.28632#page=16)

1. 從 VRM 1.0 的 `humanoid.humanBones` 找出對應 glTF 節點，擷取人形骨的語意名稱、父子關係及靜止變換。略過中介骨時合成其變換，寫回仍以原節點的父骨為基準。 [VRM 人形骨規格](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md)
2. 校正骨架軸向與尺度，對齊 VRM 原本的 T-pose 靜止基準。若曾轉到 A-pose，寫回前換回原基準。 [VRM T-pose 規格](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/tpose.md)
3. 把 JCA 輸出的逐幀旋轉轉成目標父骨座標下的局部四元數，把世界座標下的根位移換算到目標根節點的父座標。若匯出 VRMA，人形骨的平移軌只寫給 `hips`。 [VRMA 規格](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm_animation-1.0/README.md)
4. 人形骨交給 JCA，髮與裙擺交給 SpringBone。先用已知的轉身、抬手和移步測試寫回，再用 JCA 輸出檢查朝向、腳滑與根軌跡。 [VRM SpringBone 規格](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_springBone-1.0/README.md)

## 詳細參考

- `/home/box/research/jca/JCA.md` 第一部分整理方法、訓練、推論與評測，第二部分記錄 VRM 轉換推測。
- `/home/box/research/jca/fig_*.png` 包含 `fig_architecture.png`（論文圖 2）與 `fig_results.png`（論文圖 3）。
