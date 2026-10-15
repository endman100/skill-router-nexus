# Prompt Templates

每次填入實際附圖編號與本案例物件；保留簡短共同設定，避免加入參考圖沒有的畫風或裝飾。所有生成、重試與編輯都附全部原始圖；若參考槽不足，先省略可選引導，仍放不下就說明，不能偷偷少附原始圖。

## Base scene

```text
Create ONE complete scene source image from <user prompt>.
<When supplied: Images 1–N are all original references and define design and style.>
Preserve <specified style, major objects, arrangement, materials, time and lighting>.
Horizontal eye-level viewpoint, natural perspective, readable overall environment.
No added labels, borders, collage, overhead view, cutaway or 3D-render treatment.
```

## Alternate view

```text
Images 1–N are all original references. Image N+1 is the accepted base scene.
Create ONE view <A / B / C> of this SAME scene: <camera location and direction>.
Keep all objects, openings and the light source in their existing world positions.
Keep the same design, palette, materials, time and rendering style.
Horizontal eye-level camera, matching viewing height; only camera position changes.
Show naturally visible objects; allow occlusion and objects behind camera to be absent.
Complete unseen areas minimally and coherently. No additional decor, labels or borders.
```

只有 prompt 時把輸入敘述改為「Image 1 is the accepted base scene」，並沿用原始 prompt。
對 A 加上：`Move to the opposite side and look back across the scene. Show the previously unseen opposite background. Do not mirror the base or relocate its doors. A door behind camera stays out of view. Keep daylight world-fixed; its screen direction may reverse.`

## Detail / repair

```text
Using all original references and the accepted base, create ONE close-up of <existing detail>.
Preserve its exact design, material, color and rendering style. Show it at a readable scale.
This is an in-scene detail, not a new design or whole-room image. No added text or borders.
```

修圖前先查看目標，附全部原始參考、必要基準與修圖目標，指定 `Change ONLY <failed property>; preserve <viewpoint, all other objects, style and framing>.` 不以重做整個場景處理單一錯誤。
