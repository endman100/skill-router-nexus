---
name: hairdeck-vrm-hair-cards
description: "用於以 HairDeck 從單張角色圖或髮型點雲生成可編輯的 3D 髮片，或替 VRM／VRoid 3D avatar 換髮型。適合將頭髮 spring bones 接到既有 humanoid bones、保留 blendshape／expression 綁定，以及評估 VRM 匯出與執行時的髮絲晃動。"
---

# HairDeck 單圖髮片生成與 VRM 頭髮綁定

Yuze He 等人的《HairDeck: Animation-Ready Stylized Hair Cards from a Single Image》（arXiv:2610.40599v1）從角色圖或髮型點雲生成靜止姿勢的風格化髮片與髮骨鏈。
每張髮片是帶寬度與厚度的幾何帶，可單獨編輯。也可將符合表示法的既有髮片編碼後，單獨生成髮骨鏈。 [論文 §3、§4.6](https://arxiv.org/html/2610.40599v1)

## 方法與管線

1. **輸入條件**。單圖用髮部與臉部遮罩取方形裁圖，外部圖片以 SAM 3 取得遮罩，再由凍結的 DINOv3 ViT-L/16 編碼。點雲路線用凍結的 Dora-VAE 編碼髮型表面點。
   圖像路線以臉寬與臉部包圍盒頂部中心定義共用頭部座標，訓練時使用多視角渲染、合成風格增強及重新風格化圖片，目標皆為靜止姿勢的髮片。
2. **一張髮片一個 token**。Card VAE 將可變長的控制點序列（位置、寬度、厚度）壓成 32 維潛向量，按弧長解碼。
   髮根位置、髮根寬向、菱形或三角形截面、存在旗標與潛向量合成 40 維 token。
3. **整組去噪與成網**。無槽位位置嵌入的 set diffusion transformer（DiT）透過 flow matching 聯合生成最多 192 個槽位，以存在旗標選出有效髮片。
   沿中心線用 Bishop frame 傳遞寬向並掃掠截面，得到帶逐片 UV 的髮片網格。
4. **生成髮骨與蒙皮**。第二個 set DiT 以髮片 tokens 為條件，生成最多 48 條骨鏈，每條包含以弧長取樣的路徑、關節數、剛度與存在旗標。
   幾何蒙皮查看髮片中心線下段 60%。若最近骨鏈的平均距離低於 0.4 個臉寬，即在鏈根起算的 0.05 個臉寬弧長內，將權重從 `head` 漸移至骨鏈，並在相鄰鏈段間混合。未匹配的髮片隨頭部剛性移動。

方法及實作細節見[論文 §3 與附錄 A](https://arxiv.org/html/2610.40599v1)。

## 結果與限制

論文採用源自 VRoid 的 CHARM 資料集，使用 36,440 個訓練髮型。時間在單張 RTX A6000、batch size 1 下量測，計到髮片輸出、成網之前。 [論文 §4.1–4.5](https://arxiv.org/html/2610.40599v1#S4)

| 評估 | 論文結果 |
| --- | --- |
| 100 個 CHARM 測試髮型的點雲 | 對 CHARM，Chamfer distance 由 0.0117 降至 0.0066（約 44%），髮片方向誤差由 40.0° 降至 16.8°，每髮型由 33.7 秒降至 1.01 秒（約 33 倍速）。 |
| 單圖，76 個帶完整模型的測試角色與 40 張外部插畫 | 渲染測試角色的對齊後 Chamfer distance 為 0.0089、IoU 為 0.725。論文報告兩組失敗率為 3.5% 與 10.0%，每圖 1.33 秒。 |
| 58 個原有髮骨鏈的測試髮型 | 在原作者髮片上，生成骨鏈的動態相關係數為 0.702，檢索基線為 0.622；以單圖生成的髮片為條件時，骨鏈召回率為 0.390。 |

- 移除頭部座標正規化後，單圖未對齊的 Chamfer distance 從 0.0136 升至 0.0189，對齊後維持 0.0089。這組消融顯示正規化主要改善髮型在頭部的位置與尺度。 [論文 §4.4](https://arxiv.org/html/2610.40599v1#S4)
- 訓練偏向 VRoid 風格；極短髮、寫實透明貼圖式髮片超出訓練範圍。帽子、蝴蝶結、背景或道具若落在遮罩內，可能變成多餘髮片；少見的頭頂放射狀骨鏈容易漏生。 [論文 §5、附錄 F](https://arxiv.org/html/2610.40599v1#S5)
- v1 產生幾何與 UV，完整貼圖需另行製作，展示髮色可從圖中取樣。
  官方 2026-11-05 更新另發布逐片色彩模型，GLB 與 VRM 可攜帶色彩，VRM 匯出器可建立色彩圖集。色彩模型的量化結果與自訂 VRM 1.0 角色的相容性數據為未知／未公開（2026-11-24）。 [論文 §5](https://arxiv.org/html/2610.40599v1#S5) · [官方發布說明](https://github.com/hyz317/HairDeck#-updates) · [匯出前處理](https://github.com/hyz317/HairDeck/blob/main/hairdeck/vrm/prep.py)

## 應用於 VRM

### 論文與官方實作

- **資產輸入與輸出**。角色圖 → 髮片幾何／UV 與骨鏈 → 套到既有角色。公開推論輸出 `cards_seed0.json`、`chains_seed0.json` 與附或不附頭部代理網格的髮型 GLB。
  使用 Blender 4.2 LTS 和 VRM Add-on 的官方匯出器可用隨附的 VRoid 範本或具備頭部校準資料的 VRM 0.x 角色，寫出新 `.vrm`，並可另產生轉頭影片。單張參考圖供製作髮型資產，模型未提供人體動作或臉部表情的時間序列。 [論文附錄 A](https://arxiv.org/html/2610.40599v1#A1) · [官方輸出說明](https://github.com/hyz317/HairDeck#-outputs) · [角色配置](https://github.com/hyz317/HairDeck/blob/main/hairdeck/vrm/body.py)
- **Humanoid bones**。官方匯出先反轉目標角色的頭部正規化（座標移回臉部錨點，寬厚依臉寬還原），再轉入角色的 Blender 靜止姿勢座標。從 humanoid mapping 找到 `head`，將新髮骨根掛在 `head` 下，髮片頂點綁到 `head` 與額外髮骨。Humanoid mapping 由底模提供。 [匯出前處理](https://github.com/hyz317/HairDeck/blob/main/hairdeck/vrm/prep.py) · [髮骨與蒙皮實作](https://github.com/hyz317/HairDeck/blob/main/blender/vrm_hair.py)
- **Blendshapes／表情**。髮片及骨鏈輸出沒有臉部 morph targets 或表情權重。官方 VRM 0.x 匯出檢查會比對 `blendShapeMaster`；已移除髮網格上的綁定可被移除。VRM 1.0 的對應表情定義是 `VRMC_vrm.expressions`，可引用目標模型的 morph targets。 [匯出檢查](https://github.com/hyz317/HairDeck/blob/main/hairdeck/vrm/check.py) · [VRM 1.0 規格](https://github.com/vrm-c/vrm-specification/tree/master/specification/VRMC_vrm-1.0)
- **Spring bones**。論文以 UniVRM 的更新方式模擬頭髮，條件為 60 fps、預測剛度、drag 0.4、重力 0、無 collider。
  公開 VRM 0.x 匯出為每條使用中的髮骨鏈寫入 `secondaryAnimation` 群組，可引用角色既有 collider，並保留非髮 spring groups。衣服、胸部等二次動態的生成未在論文評估。 [論文 §3.4、附錄 A](https://arxiv.org/html/2610.40599v1#A1) · [官方匯出實作](https://github.com/hyz317/HairDeck/blob/main/blender/vrm_hair.py)

### 工程推論，論文未驗證

1. **替換自訂髮型**。在目標角色的靜止姿勢量臉寬與臉部頂部中心，依匯出器的 body 設定對齊座標。確認髮根貼合、後腦覆蓋和髮梢方向。若頭髮與臉共用網格或與衣物共用骨骼，先在編輯器確認移除範圍及依賴；官方匯出器以網格名稱含 `hair` 辨識髮網格。 [官方角色配置](https://github.com/hyz317/HairDeck/blob/main/hairdeck/vrm/body.py) · [髮網格辨識實作](https://github.com/hyz317/HairDeck/blob/main/blender/vrm_hair.py)
2. **接入動作與表情**。即時動捕或動畫播放器依目標 humanoid mapping 和靜止姿勢套用身體、頸及 `head` 的旋轉，新增髮骨跟隨父節點。另用臉捕／口型來源驅動目標角色實際存在的眨眼、母音等表情，依輸出版本使用 0.x blendshape 群組或 1.0 expression，重新匯入確認綁定仍指到正確網格與 morph target。
3. **設定物理與版本**。目標若為 VRM 1.0，使用相容工具遷移匯出結果或重建 `VRMC_springBone`，依父子順序填入鏈節點並檢查剛度、阻尼、碰撞半徑和 collider groups。衣物與胸部沿用底模的設定並個別測試。用快速轉頭、點頭或低頭測試穿模、突跳和停下後的回彈。 [VRM 0.x 規格](https://github.com/vrm-c/vrm-specification/tree/master/specification/0.0) · [VRM 1.0 SpringBone 規格](https://github.com/vrm-c/vrm-specification/tree/master/specification/VRMC_springBone-1.0)
4. **選擇即時或烘製**。將生成與換髮放在離線製作階段，新 `.vrm` 保存網格、蒙皮與 spring 設定。即時播放先更新動作與表情，再讓相容 runtime 解算髮骨。
   若要固定鏡頭效果，在 DCC 模擬後將髮骨局部變換烘到支援一般骨骼曲線的動畫資產或直接渲染影片。播放烘製曲線時停用同一骨鏈的即時解算。
   `.vrma` 可用於支援的 humanoid／表情動畫，髮骨烘製需另行保存。 [UniVRM 更新順序](https://vrm.dev/en/api/api_update/) · [VRM Animation 規格](https://vrm.dev/en/vrma/)

## 來源與可用性

- 論文版本為 2026-10-29 上傳的 v1。 [Hugging Face Papers](https://huggingface.co/papers/2610.40599) · [arXiv 摘要](https://arxiv.org/abs/2610.40599v1) · [HTML 全文](https://arxiv.org/html/2610.40599v1)
- 官方展示包含轉頭樣例，提供線上單圖示範。 [專案頁](https://hyzcluster.github.io/HairDeck/) · [官方 Hugging Face Space](https://huggingface.co/spaces/hyz317/HairDeck)
- 截至 2026-11-24，官方已公開程式碼和模型權重，兩者採 Apache-2.0。SAM 3、DINOv3 需另行接受各自授權。 [GitHub](https://github.com/hyz317/HairDeck) · [官方模型卡](https://huggingface.co/hyz317/HairDeck)
- CHARM 發布測試資料、訓練清單與前處理流程；原始 VRoid 訓練角色未由 CHARM 再散布，資料卡說明如何取得原始來源。 [CHARM 資料集](https://huggingface.co/datasets/hyz317/CHARM)
