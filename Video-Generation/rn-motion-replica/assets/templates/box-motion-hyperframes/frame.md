# Codex × DeepSeek Box Motion — Visual Spec

## Intent

Recreate the motion language of a clean technical node diagram: outlined cards arrive one at a time, orthogonal connector lines draw between them, and the graph changes state without rebuilding the whole page. The deliverable is an original motion-study sample, not a copy of any source script, presenter, subtitles, or footage.

## Canvas

- 1920 × 1080, 30 fps, 35 seconds, 16:9
- Warm paper background: `#F4F0DD`
- Outer technical frame: 5 px near-black line with a 10 px offset shadow
- Subtle pale green / lavender radial washes; no texture that competes with text

## Palette

- Ink: `#171914`
- Paper: `#F4F0DD`
- White card: `#FFFEF6`
- Focus yellow: `#F2C94C`
- Signal red: `#E95B4E`
- Muted olive: `#B9B59B`
- Soft shadow: `#D6D0B9`

## Typography

- Chinese and labels: Noto Sans JP (bundled CJK font, 400 / 700)
- Technical metadata: JetBrains Mono / SFMono-Regular / monospace
- No rounded SaaS typography. Keep labels compact and editorial.

## Card language

- 4 px ink borders, 4–10 px corner radius
- 7–9 px hard offset shadow, never a large blurred shadow
- Yellow cards = prompt / target / active state
- White cards = tools / routing / neutral state
- Black mini tiles = sequence number or status
- Each card gets one small metadata line so the page feels authored, not like placeholder rectangles

## Motion language

- Card entrance: `scale .82 → 1`, `opacity 0 → 1`, optional `y 18 → 0`, 0.45–0.6 s, `power3.out`
- Line entrance: SVG stroke draw, 0.35–0.6 s, `power2.out`
- State change: outgoing cluster compresses to `.94` while fading; incoming cluster starts at `.97`, overlaps by about 0.15 s, no cartoon bounce
- Only one new reading target enters at a time
- Final scene transition: a single medium-energy horizontal push at ~31.2 s
- Holds are intentional; no infinite idle loops

## Density and composition

- Main graph occupies the central 70% of the frame
- Header and small edge marks anchor the composition to the frame
- 6–10 visible authored elements at graph peaks, but no decorative UI chrome beyond the reference language
- Connector paths sit behind cards and use orthogonal bends
