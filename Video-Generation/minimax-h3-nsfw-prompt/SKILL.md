---
name: minimax-h3-nsfw-prompt
description: "為 MiniMax H3 Ref2VA 生成與優化結構化影片 prompt。適用於動漫風格 NSFW 影片提示詞設計，包含角色參考、動作控制、音訊隔離與模組化變數。觸發關鍵字：MiniMax H3、Ref2VA、影片 prompt、角色聲音、NSFW prompt。"
type: workflow
lifecycle: active
---

# MiniMax H3 NSFW Prompt 工程

建立結構化的 MiniMax H3 Ref2VA prompt，透過模組化模板控制角色身份、姿勢、鏡頭、音訊與背景。

## 何時使用

- 要為指定角色生成不同性愛場景的影片 prompt
- 需要套用模組化模板，快速更換姿勢、鏡頭、動作
- 角色特徵與服裝已固定，只需調整場景相關變數
- 要保持角色一致性的同時產出多種性愛動作

## 核心結構

每個 prompt 必須依照以下順序：

1. `subject_definitions` — 定義角色、參考圖、音訊職責
2. `summary` — 簡短概述
3. `retention_analysis` — 鎖定要保留的元素
4. `detailed_description` — 主要控制段（姿勢、鏡頭、動作、聲音）
5. `overall_soundscape` — 聲音總結
6. `non_diegetic_music` — 通常寫 `N/A`

## 參考圖規則

| 參考 | 用途 | 權重 |
|------|------|------|
| `<Picture 1>` | 女性身份、臉、身體、服裝 | `fully_preserved` |
| `<Picture 2>` | 男性外觀（可選） | `weak_reference` |
| `<Picture 3>` | 插入細節（pussy 與 dick） | reference（固定使用 `assets/penetration-reference.png`） |
| 背景 | 純文字描述 | 不依賴參考圖 |

- 只描述想要出現的物品，不要提到不想出現的東西
- 男性若不需要出鏡臉部，設為 `weak_reference`
- `<Picture 3>` 固定使用 skill 內的 `assets/penetration-reference.png`
- 若有提供 `<Picture 1>` 或 `<Picture 2>`，必須從中確認角色特徵與服裝資訊

## 模組化變數

| 變數 | 用途 | 填寫原則 | 範例 |
|------|------|---------|------|
| `{{female_appearance}}` | 女性外貌特徵 | 只寫臉、頭髮顏色、頭髮樣式、眼睛顏色、膚色、體型、胸部大小，不寫服裝。必須從 `<Picture 1>` 確認。換動作時必須保持不變 | same face, long pink-to-orange hair with bangs, green eyes, fair skin, curvy body with large breasts |
| `{{female_outfit_exposure}}` | 女性服裝與露出程度 | 寫服裝類型＋顏色＋哪些部位露出；未暴露部位必須寫上服裝與顏色。必須從 `<Picture 1>` 確認 | She wears a blue top with pink ribbon, blue skirt, black thigh-high socks, and red shoes, with breasts fully exposed and pussy exposed |
| `{{male_outfit_exposure}}` | 男性服裝與露出程度 | 必須從 `<Picture 2>` 確認服裝（不可預設裸體），並說明哪些部位拉下或露出 | He wears a blue t-shirt and dark pants pulled down, with his cock fully exposed and already inside her |
| `{{background}}` | 場景背景 | 純文字描述，只寫想要的場景元素，不要提到不想出現的物品 | a simple room with white walls and light wooden floor |
| `{{pose_description}}` | 身體放置位置 | 靜態描述：身體怎麼擺、手在哪、視線方向、生殖器是否插入及放在哪、哪些部位是可視的、男性是否部分可見。必須使用專業性愛姿勢術語（missionary、mating press、doggy style、cowgirl、reverse cowgirl、spooning、standing rear、prone bone、standing leg-up）。必須明確寫男性臉部不在畫面中（male face out of frame）。手部描述需明確：掌心貼牆、手背貼牆、或手指抓住物件 | standing in a standing leg-up position, back pressed against the wall, one leg raised high, hands raised near shoulders with back of hands pressed against the wall, male face out of frame |
| `{{character_position}}` | 角色所在位置 | 描述與四周物件的空間關係，必須明確寫身體是否接觸地面或物件（lying on / sitting on / pressed against），避免角色浮空 | pressed against the white wall, body in contact with the wall |
| `{{camera_angle}}` | 鏡頭角度 | 不可留白；只寫觀看角度，不寫移動；必須指定焦點部位（focused on XX）；必須與身體位置在物理上合理 | Side view, focused on her pussy and the penetration |
| `{{camera_movement}}` | 鏡頭動作 | 預設包含輕微旋轉與位移；寫晃動、平移、旋轉等 | Camera side view with slight handheld movement |
| `{{motion_type}}` | 動作類型簡稱 | 用短詞概括動作類別，必須使用專業性愛姿勢術語 | fast standing leg-up |
| `{{motion_description}}` | 動作過程 | 動態描述：如何移動、抽插方式、身體如何隨動作晃動、插入是否全程保持連接 | He holds her raised leg with one hand, thrusting hard and fast from the front. Penetration stays connected throughout |
| `{{female_expression}}` | 表情 | 必須有至少兩種動態並在影片中輪替出現：開合單眼或雙眼、微微吐出舌尖後快速收回、咬嘴唇、翻白眼等。不可只寫靜態表情。舌頭不要全吐出 | tongue tip slightly sticking out then quickly retracting, alternating with biting her lip, eyes half-closed then opening |
| `{{female_body_reaction}}` | 身體反應 | 預設包含胸部晃動、臀部晃動；若可見則加入 pussy 一開一合 | breasts bouncing, ass bouncing, pussy opening and closing with each thrust |
| `{{dialogue}}` | 語音內容 | 一定要中日英文混合；預設擬聲詞為主，除非有指定臺詞 | 嗯……ah……嗯啊……んっ……ah…… |

## 完整模板

```text
subject_definitions:
<Subject 1> is the adult woman as she appears in <Picture 1>: {{female_appearance}}. {{female_outfit_exposure}}.
<Subject 2> is the adult man as he appears in <Picture 2>. {{male_outfit_exposure}}.
<Subject 3> is {{background}}.
<Picture 1> is the source for the woman's identity, face, hair, body, and outfit.
<Picture 2> is a weak reference for the man's general appearance only. Do not emphasize his face or upper body.
<Picture 3> is the reference for the penetration appearance, showing both pussy and dick during insertion.
<Audio 1> is the voice-timbre reference only for <Subject 1>. Use the breathy vocal quality and speaking style. Do not copy any unrelated words or dialogue from it.

summary:
[reference generation + first-frame lock + audio reference] 2d anime style, dynv2, continuation with bright lighting, high saturation, and vivid colors. {{background}}. She is {{pose_description}} {{character_position}} with {{female_expression}}. {{camera_angle}}. {{motion_description}}. {{camera_movement}}. Soft high-pitched breathy moans with onomatopoeia matching <Audio 1> timbre.

retention_analysis:
<Subject 1> (appears throughout [Shot 1]): fully_preserved - exact face, hair, body, and exposure from <Picture 1>.
<Subject 2> (appears throughout [Shot 1]): weak_reference.
<Subject 3> (appears throughout [Shot 1]): fully_preserved - {{background}}.
<Picture 1> (identity): fully_preserved.
<Picture 2> (identity): weak_reference - general appearance only, do not focus on face.
<Picture 3> (penetration detail): reference - use for pussy and dick appearance during insertion.
<Audio 1>: reference - breathy vocal quality and speaking style only.

detailed_description:
[Shot 1] 2d anime style, dynv2, bright lighting, high saturation, vivid and colorful. {{background}}. {{camera_angle}} of the woman {{pose_description}} {{character_position}}. {{female_outfit_exposure}}. {{female_expression}}. {{motion_description}}. {{female_body_reaction}}. Continuous {{motion_type}}. {{camera_movement}}. The penetration matches the appearance in <Picture 3>, showing both pussy and dick. Clear wet thrusting, skin slapping, and impact sounds synced to the fast motion. She produces soft high-pitched breathy moans mixed with onomatopoeia matching <Audio 1> timbre. She says: <d>[Chinese] {{dialogue}}</d> Background is {{background}}.

overall_soundscape:
Quiet room tone, clear wet thrusting, skin slapping, and impact sounds synced to the fast motion. Soft high-pitched breathy moans, onomatopoeia, and short spoken lines using <Audio 1> timbre.

non_diegetic_music:
N/A
```