# Visual grammar

Use this as a neutral dark-theme default. Override it when the user supplies brand rules.

## Layer hierarchy

```text
SurfaceCanvas
├─ VideoChrome: progress rail + chapter marker
├─ SceneStage: headline + diagram/panel/illustration + annotation
└─ CaptionTrack: independent bottom layer, highest z-index
```

## Layout families

1. Left narrative: kicker, large headline, then diagram.
2. Centered hero: one title and one object at the visual center.
3. Two-column comparison: panels separated by a gap, badge, arrow, or `VS` relation.
4. Horizontal process: equal nodes along one baseline with connectors behind them.

Use one dominant family per scene. Avoid combining a dense grid, network, comparison, and full UI panel in one shot.

## Default 1920×1080 safe regions

| Region | Default |
|---|---:|
| left/right safe margin | 100 px |
| top safe margin below chrome | 90 px |
| scene-stage bottom | 880 px |
| caption bottom | 60 px |
| caption maximum width | 1660 px |

Remeasure when aspect ratio, title length, caption size, or supplied UI assets change.

## Color roles

| Token | Default value | Role |
|---|---|---|
| `surface.canvas` | `#1e1e1e` | background |
| `surface.panel` | `#292929` | cards and windows |
| `border.subtle` | `#3a3a3a` | inactive borders and connectors |
| `text.primary` | `#f5f5f5` | titles, labels, captions |
| `text.muted` | `#b8b8b8` | kicker and secondary explanation |
| `accent.primary` | `#f6a21a` | current focus, path, underline |
| `semantic.danger` | `#ff5158` | error, drift, harmful outcome |
| `semantic.success` | `#2dcc71` | pass, completion, containment |
| `series.purple` | `#7845e7` | neutral category distinction |

Treat semantic roles as more important than exact hex values. Never use danger/success colors as decoration when no matching state exists.

## Typography and captions

- Use a heavy sans face for claims and Chinese headlines.
- Use monospace for filenames, code, terminal text, and node identifiers.
- Keep captions in a dark rounded capsule independent from diagram geometry.
- Prefer one or two short caption lines; group text by phrase rather than single characters.
- Measure text before assigning fixed card widths. Do not shrink a core claim until it becomes unreadable.

## Density and assets

Use generous negative space. One diagram should answer one semantic question. Include real UI only when the user supplies it and the narration discusses implementation. Use illustration as a metaphor or chapter reset, not as background decoration.
