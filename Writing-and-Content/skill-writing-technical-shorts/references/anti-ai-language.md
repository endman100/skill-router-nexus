# Anti-AI language gate

Use this gate after facts and structure are stable. The goal is direct spoken Traditional Chinese, not artificial roughness. Preserve technical facts and the author's judgment while removing reusable writing shells.

## Hard bans

Rewrite these patterns whenever they appear in the spoken body.

### Binary contrast shells

- `不是 A，而是 B`
- `並非 A，而是 B`
- `不在於 A，而在於 B`
- `不只是 A，更是 B`
- `不僅 A，還／更 B`
- `與其 A，不如 B`

Delete the shell and state the measurable difference directly.

Bad: `這次升級不只是速度更快，而是改變整套流程。`

Better: `舊版完成這個流程要分兩次處理；新版能在同一次操作裡完成。`

### Command-template openings

- `別急著 X，先 Y`
- `先別 X，先 Y`
- `順序別反了`
- `別搞反了`
- `記住這句話`

Open with the concrete problem, failure, or observation instead.

### Fake-insight markers

- `真正`、`其實`、`本質上`
- `核心在於`、`關鍵在於`
- `說白了`、`歸根結底`
- `更重要的是`
- `結果有點出乎意料`
- `這說明`、`這背後`

Remove the marker and start with the evidence or judgment it was announcing.

### Lecture-colon setup

- `我的結論是：`
- `原因很簡單：`
- `重點是：`
- `分成三類：`
- `更重要的是：`

A colon is acceptable only after a concrete category noun that introduces an actual inventory.

### Clickbait and canned social language

- `大部分人以為`
- `這根本是在`
- `愣住了`
- `更扯的是`
- `結果呢`
- `震撼全球`
- `深入探討`
- `想像一下`
- `對一般使用者來說`
- `懶人包｜`
- `👇`

Replace these with the exact event, behavior, affected user, or result.

## Semantic review

The validator can flag some of these, but a reviewer must decide whether the repair is complete.

### Exact nouns instead of vague referents

Replace `東西`、`這件事`、`這些`、`一類`、`幾個方向` with the actual category. Complete dangling phrases such as `這條`、`這篇`、`這個` with `影片`、`論文`、`工具` or the correct noun.

### Named comparisons instead of vague improvement

Do not leave `更適合`、`更像`、`更自然`、`更高級` unsupported. Name:

1. the predecessor or earlier method;
2. the same task, input, or condition;
3. the old behavior;
4. the new behavior;
5. the practical consequence.

Bad: `新版生成得更自然。`

Better: `舊版改動角色服裝時，臉部特徵常會跟著變；新版在同一種編輯裡能保留較多原本特徵。`

### Concrete consequences instead of pressure or slogans

Remove phrases such as `差距會被迅速拉開`、`新的分水嶺`、`能力飛輪`、`時代分水嶺`、`作者痕跡`. State the visible result, saved work, failure mode, or cost.

## Final repair pass

For every suspect sentence:

1. Delete the reusable shell.
2. Name the actor, version, task, and observable change.
3. Keep only facts supported by primary sources.
4. Add one short example if it makes a difficult change concrete.
5. If the explanation still depends on several unfamiliar terms, remove that technical detail.
