# Motion grammar

Keep the camera fixed by default. Move elements to explain a relation, hierarchy, or state change rather than to add constant activity.

## Core sequence

1. `Establish`: make the headline and inactive scaffold readable.
2. `Focus`: highlight the node, card, or path currently discussed.
3. `Mutate`: preserve geometry and change the relevant state.
4. `Explain`: append a guard, warning, result, row, or verdict.
5. `Exit`: replace or fade the scene stage while chrome and captions remain independent.

## Motion families

| Family | Properties to change | Preferred sequence |
|---|---|---|
| title + underline | opacity, translateY, underline scaleX | title → underline |
| process activation | border, fill, glow, connector state | scaffold → nodes in reading order |
| error propagation | node and connector semantic color | fault → downstream path |
| loose tiles to grid | x, y, rotation, opacity, scale | elements → alignment → labels |
| progressive comparison | child opacity and horizontal position | claim → sides → result |
| guard insertion | badge opacity, scale, translateY | both sides → guard |
| dependency draw | SVG path length or opacity | nodes → connectors |
| mapping rows | row opacity and translateY | append without moving prior rows |
| verdict overlay | scene dimming, callout opacity and scale | completed scene → verdict |
| chapter replacement | outgoing group opacity, incoming group opacity and translateY | exit → brief reset → enter |

## Default timing ranges

Use these as starting points and adjust to speech pace:

| Change | Typical duration |
|---|---:|
| short fade or color interpolation | 0.12–0.30 s |
| label or badge entrance | 0.25–0.50 s |
| card entrance | 0.35–0.70 s |
| line draw or ordered activation | 0.20–0.45 s per item |
| grid convergence | 0.70–1.40 s |
| scene replacement | 0.35–0.80 s |

Trigger the start from the canonical narration cue. Keep the final state visible long enough to be read before the next conceptual change.

## State-change rules

- Preserve positions while changing inactive, active, error, success, or dimmed states.
- Keep connectors behind cards and animate them in the reading direction.
- Stagger repeated items only when the narration enumerates or propagates across them.
- Avoid long overshoot, bounce, and decorative looping in information-dense scenes.
- Replace the scene group for chapter changes; do not force a morph between unrelated geometries.
