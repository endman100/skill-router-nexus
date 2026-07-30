---
name: skill-writing-technical-shorts
description: Use when a user requests a concise Traditional Chinese Short video script or spoken introduction for an AI model, software feature, developer tool, or other technology, especially a 650-1000 character script that explains concrete differences from the previous version without AI-flavored writing shells.
---

# Writing Technical Shorts

## Core principle

Explain one technology clearly enough for an ordinary reader to follow. Build technical detail around an observable previous-version difference, then explain only the mechanism needed to understand that difference. Let facts determine emphasis instead of forcing equal-sized sections.

## Workflow

1. Confirm the topic name and requested length. When the user gives no target, use 650-1000 non-whitespace characters. Treat 1000 as a ceiling, not a quota; stop when the comparison is clear.
2. Verify current facts with primary sources when the topic can change. Prefer official documentation, release notes, model cards, repositories, specifications, and papers. Do not rely on remembered version numbers, prices, dates, or capabilities.
3. Draft a continuous spoken script with this narrative order:
   - Open with the exact standalone sentence `什麼是 {topic}？`
   - Describe the observable problem or effect, then define the technology in one plain sentence.
   - Compare the predecessor and current version on the same task or input. State `previous behavior → current behavior → practical consequence`.
   - Add one concrete before-and-after example when it makes the change easier to picture.
   - Explain only the mechanism needed to account for that change. Omit a detail when it cannot be explained without stacking unfamiliar terms.
   - State meaningful limitations or trade-offs.
   - End with one or two sentences that judge its core technical value.
4. Read [references/review-rubric.md](references/review-rubric.md) and [references/anti-ai-language.md](references/anti-ai-language.md). Review the draft and record specific problem sentences.
5. Correct only the affected sentences or their order. Preserve sound structure and wording; do not restart the entire draft.
6. Repeat the review until readability, ordinary-reader comprehension, technical clarity, and adjacent-sentence continuity all pass.
7. When a filesystem is available, save the candidate and run:

```bash
python scripts/validate_short_script.py <draft-file> --topic "<topic>" --min-chars 650 --max-chars 1000
```

Fix every error. Treat warnings as review prompts rather than automatic failures. If the user specifies a single target, pass that value to `--target`; the legacy target mode allows ±10% by default.

## Writing rules

- Keep the spoken body within 650-1000 non-whitespace characters unless the user gives another target. Never add filler merely to approach the maximum.
- Introduce a technology in the order **problem or effect → technology name → mechanism or specification**.
- Make technical detail difference-first. Name the previous version's behavior, the current version's changed behavior, and the consequence under the same task or input.
- Do not explain a noun with another unexplained noun. Ground every unfamiliar term in an observable action or effect before naming it. If the explanation still needs a chain of new terms, rewrite it in plain language or omit it.
- Use a concrete example when it materially clarifies a difficult change. Keep the example to one or two sentences, preserve the actual conditions, and never invent a scenario or capability. If no honest short example works, omit the difficult detail.
- Prefer standard English technical terms such as `VRAM`, `token`, `API`, `MoE`, and `codec`. Write `VRAM` instead of `顯示卡記憶體`、`GPU 記憶體` or `顯存`. Briefly explain an unfamiliar term on first use, then keep its spelling consistent.
- Explain what a test result means before giving useful before-and-after numbers. Do not name or recite benchmark suites.
- Remove AI-flavored contrast shells, fake-insight markers, lecture openings, vague comparisons, and clickbait templates listed in [references/anti-ai-language.md](references/anti-ai-language.md). State the concrete claim directly.
- Omit license terms, local deployment instructions, deployment frameworks, and commands.
- Keep source links and citations outside the spoken body.
- Do not turn the script into a tutorial, parameter guide, installation guide, or feature inventory.
- Do not end with usage advice, a recommendation, a website invitation, or a call to action.
- Do not invent a predecessor. When no direct previous version exists, compare with the earlier common method and state the comparison narrowly.

## Sentence-order example

Avoid dropping a new term before its purpose or version difference is clear.

Bad: `它加入 XYZ，支援一百萬 token。`

Better: `舊版一次只能讀一份輸入；新版能同時比對多份輸入，修改其中一項時，其他內容較能維持原位。負責這個變化的元件叫做 XYZ。`

## Final delivery

Return only the polished continuous script unless the user requests the audit. Ensure the first non-empty line is exactly `什麼是 {topic}？`. If web research was required, list sources separately after the script without inserting them into the narration.
