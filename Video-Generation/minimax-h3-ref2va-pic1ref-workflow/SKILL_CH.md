# MiniMax H3 Ref2VA pic1ref 動作影片 workflow（中文版）

英文正式版為同資料夾的 `SKILL.md`。

用四個參考產出 2D 動畫動作短片（預設 5 秒）：一張女性身份圖、一張男性參考圖、一張該動作的首尾幀靜態圖、一段聲音參考。每個動作只換靜態圖和 prompt 變數，其餘 graph 固定。

本文件只講 workflow 與 prompt，不講機器操作。本 workflow 是單鏡頭 5 秒版，與通用 H3 prompt 規則（例如 `h3-prompt-writing`）衝突時以本文件為準（例如這裡 `<Picture 1>` 是身份圖，不是分鏡）。

## 1. Graph

直接使用同資料夾的 `workflow_api_template.json`（ComfyUI API 格式）。每案只需調整以下節點：

| 節點 | 輸入 | 值 |
|---|---|---|
| 35 | `image` | 該動作靜態圖檔名（同時作為首尾幀與 `<Picture 3>`） |
| 25 | `value` | `build_prompt.py` 組出的最終 prompt |
| 22 | `filename_prefix` | `video/<set>/<case>` |
| 80 | `image` | 女性身份圖（`<Picture 1>`），換女角時才改 |
| 45 | `image` | 男性角色表（`<Picture 2>`），換男角時才改 |
| 26 | `audio` | 聲音參考（`<Audio 1>`），換聲音時才改 |

預設長度 5 秒：節點 1 `length` 124、24 fps（JSON 已設好）。

目前使用的 LoRA（JSON 已設好；strength_model 與 strength_clip 相同）：

| LoRA | 來源 | 權重 |
|---|---|---|
| `minimax_h3_PDMD_DMAD_4step_r256_add_fro1_turbo_lora.safetensors` | [Civitai](https://civitai.com/models/2929860?modelVersionId=3385247) | 1.0 |
| `2dan1m_fl2va_768-000000.safetensors` | [Civitai](https://civitai.com/models/2860624?modelVersionId=3259966) | 0.6 |
| `gzani/Motion_Repair_V2.safetensors` | [Civitai](https://civitai.com/models/2890788/bunny-general-motion-continuity-repair) | 0.5 |
| `gzani/Minimax_H3_Unlocked_V2.1.safetensors` | [Civitai](https://civitai.red/models/2925727) | 0.8 |

## 2. Prompt 模板

固定六段，英文為主，中文只放在 `<d>…</d>` 裡。模板本身維持英文，另存為同資料夾的 `template.txt`。最終 prompt 一律用 `build_prompt.py` 組成：把 13 個變數寫進一個 JSON 檔，執行 `python3 build_prompt.py vars.json -o prompt.txt`，再把結果填進節點 25。不要手動套模板。

```text
subject_definitions:
<Subject 1> is the adult woman as she appears in <Picture 1>: {{female_appearance}}. {{female_outfit_exposure}}.
<Subject 2> is the adult man as he appears in <Picture 2>. {{male_outfit_exposure}}.
<Subject 3> is {{background}}.
<Picture 1> is the source for the woman's identity, face, hair, body, and outfit.
<Picture 2> is a weak reference for the man's general appearance only. Do not emphasize his face or upper body.
<Picture 3> is the third reference image: the opening frame, exact first and last frame, for composition, poses, framing, and camera angle.
<Audio 1> is the voice-timbre reference only for <Subject 1>. Use the breathy vocal quality and speaking style. Do not copy any unrelated words or dialogue from it.
summary:
[reference generation + first-frame lock + audio reference] 2d anime style, dynv2, continuation with bright lighting, high saturation, and vivid colors. {{background}}. She is {{pose_description}} {{character_position}} with {{female_expression}}. {{camera_angle}}. {{motion_description}}. {{camera_movement}}. Soft high-pitched breathy moans with onomatopoeia matching <Audio 1> timbre.
retention_analysis:
<Subject 1> (appears throughout [Shot 1]): fully_preserved - exact face, hair, body, and exposure from <Picture 1>.
<Subject 2> (appears throughout [Shot 1]): weak_reference.
<Subject 3> (appears throughout [Shot 1]): fully_preserved - {{background}}.
<Picture 1> (identity): fully_preserved.
<Picture 2> (identity): weak_reference - general appearance only, do not focus on face.
<Picture 3> (opening frame): fully_preserved.
<Audio 1>: reference - breathy vocal quality and speaking style only.
detailed_description:
[Shot 1] 2d anime style, dynv2, bright lighting, high saturation, vivid and colorful. {{background}}. {{camera_angle}} of the woman {{pose_description}} {{character_position}}. {{female_outfit_exposure}}. {{female_expression}}. {{motion_description}}. {{female_body_reaction}}. Continuous {{motion_type}}. {{camera_movement}}. It opens and ends on <Picture 3>. She produces soft high-pitched breathy moans mixed with onomatopoeia matching <Audio 1> timbre. She says: <d>[Chinese] {{dialogue}}</d>
overall_soundscape:
Quiet room tone, clear wet thrusting, skin slapping, and impact sounds synced to the fast motion. Soft high-pitched breathy moans, onomatopoeia, and short spoken lines using <Audio 1> timbre.
non_diegetic_music:
N/A
```

模板沿革：原始版有一張插入細節參考圖當 `<Picture 3>`、靜態圖是 `<Picture 4>`。拿掉插入參考圖後只做最小修改：刪掉兩行 Picture 3 插入參考說明與 detailed_description 裡的「The penetration matches the appearance in <Picture 3>…」，`<Picture 4>` 改成 `<Picture 3>`、`fourth reference image` 改成 `third reference image`。

## 3. 13 個變數怎麼填

| 變數 | 填寫原則 | 範例 |
|---|---|---|
| `female_appearance` | 只寫臉、髮色、髮型、眼睛、膚色、體型、胸部大小，不寫服裝。從 `<Picture 1>` 取得，換動作時保持不變 | same face, long pink-to-orange hair with bangs, green eyes, fair skin, curvy body with large breasts |
| `female_outfit_exposure` | 服裝種類＋顏色＋哪些部位露出；沒露出的部位也要寫服裝與顏色。從 `<Picture 1>` 取得 | She wears a blue top with pink ribbon, blue skirt, black thigh-high socks, and red shoes, with breasts fully exposed and pussy exposed |
| `male_outfit_exposure` | 從 `<Picture 2>` 取得服裝（不可預設裸體），寫哪些部位拉下或露出 | He wears a blue t-shirt and dark pants pulled down, with his cock fully exposed and already inside her |
| `background` | 純文字，只寫想要的場景元素，不提不想出現的東西 | a simple room with white walls and light wooden floor |
| `pose_description` | 靜態描述：身體怎麼擺、手在哪、視線、生殖器是否插入與位置、哪些部位可見、男性是否部分可見。用專業姿勢術語（missionary、standing missionary、cowgirl position、reverse cowgirl position、doggy style、mating press、prone bone、spooning、standing carry、full nelson、piledriver、amazon position、upright straddle 等；其他動作 fingering、handjob、footjob、grinding、just the tip、ejaculation、orgasm）。必須寫男性是否露臉（male face out of frame / visible / partially visible）。手部要明確：掌心貼牆、手背貼牆、或手指抓住物件 | standing in a standing leg-up position, back pressed against the wall, one leg raised high, hands raised near shoulders with back of hands pressed against the wall, male face out of frame |
| `character_position` | 與周圍物件的空間關係，明確寫身體有沒有接觸地面或物件（lying on / sitting on / pressed against），避免浮空 | pressed against the white wall, body in contact with the wall |
| `camera_angle` | 不可留白；只寫觀看角度不寫移動；必須指定焦點（focused on …）；要和身體位置在物理上合理 | Side view, focused on her pussy and the penetration |
| `camera_movement` | 預設帶輕微旋轉與位移；寫晃動、平移、旋轉等 | Camera side view with slight handheld movement |
| `motion_type` | 用專業術語的短詞概括動作 | fast standing leg-up |
| `motion_description` | 動態描述：怎麼動、抽插方式、身體怎麼隨動作晃、插入是否全程保持連接 | He holds her raised leg with one hand, thrusting hard and fast from the front. Penetration stays connected throughout |
| `female_expression` | 先選一個主表情（happy、scared、sad、angry、horrified、ahegao、exciting、estrus、naughty、moaning），再加至少兩種動態輪替（pout、raised eyebrow、nose blush、blush、half-closed eyes、biting lip、eyes briefly rolling up）。不可只寫靜態表情 | ahegao with half-closed eyes and blush |
| `female_body_reaction` | 預設胸部晃動、臀部晃動；可見時加 pussy 一開一合 | breasts bouncing, ass bouncing, pussy opening and closing with each thrust |
| `dialogue` | 中日英混合，預設以擬聲詞為主，除非有指定台詞 | 嗯……ah……嗯啊……んっ……ah…… |

### 一般寫法規則
- 只描述想出現的東西，不寫「不要出現 X」。
- 男性不需露臉時一律 weak_reference 並寫 male face out of frame。
- 全文 1000 英文字以內。
