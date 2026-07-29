---
name: skill-writing-technical-shorts
description: Use when a user requests a concise Traditional Chinese Short video script or spoken introduction for an AI model, software feature, developer tool, or other technology, especially around 720 Chinese characters.
---

# Writing Technical Shorts

## Core principle

Explain one technology clearly enough for an ordinary reader to follow while preserving the technical mechanism. Keep the script topic-independent and let facts determine emphasis instead of forcing equal-sized sections.

## Workflow

1. Confirm the topic name and requested length. Default to about 720 non-whitespace characters when the user gives no other target.
2. Verify current facts with primary sources when the topic can change. Prefer official documentation, release notes, model cards, repositories, specifications, and papers. Do not rely on remembered version numbers, prices, dates, or capabilities.
3. Draft a continuous spoken script with this narrative order:
   - Open with the exact standalone sentence `什麼是 {topic}？`
   - Define the technology and establish what problem it addresses.
   - Explain the main technical features and mechanism.
   - Compare it with its predecessor or the previous common approach.
   - State meaningful limitations or trade-offs.
   - End with one or two sentences that judge its core technical value.
4. Read [references/review-rubric.md](references/review-rubric.md), review the draft, and record specific problem sentences.
5. Correct only the affected sentences or their order. Preserve sound structure and wording; do not restart the entire draft.
6. Repeat the review until readability, ordinary-reader comprehension, technical clarity, and adjacent-sentence continuity all pass.
7. When a filesystem is available, save the candidate and run:

```bash
python scripts/validate_short_script.py <draft-file> --topic "<topic>" --target 720
```

Fix every error. Treat warnings as review prompts rather than automatic failures. If the user specifies another length, pass that value to `--target`.

## Writing rules

- Keep the spoken body near the target length; the validator allows ±10% by default.
- Introduce a technology in the order **problem or effect → technology name → mechanism or specification**.
- Prefer standard English technical terms such as `VRAM`, `token`, `API`, `MoE`, and `codec`. Write `VRAM` instead of `顯示卡記憶體`、`GPU 記憶體` or `顯存`. Briefly explain an unfamiliar term on first use, then keep its spelling consistent.
- Explain what a test result means before giving useful before-and-after numbers. Do not name or recite benchmark suites.
- Omit license terms, local deployment instructions, deployment frameworks, and commands.
- Keep source links and citations outside the spoken body.
- Do not turn the script into a tutorial, parameter guide, installation guide, or feature inventory.
- Do not end with usage advice, a recommendation, a website invitation, or a call to action.
- Do not invent a predecessor. When no direct previous version exists, compare with the earlier common method and state the comparison narrowly.

## Sentence-order example

Avoid dropping a new term before its purpose is clear.

Bad: `它加入 XYZ，支援一百萬 token。`

Better: `為了延長可處理內容，它加入 XYZ，將上下文上限擴到一百萬 token。`

## Final delivery

Return only the polished continuous script unless the user requests the audit. Ensure the first non-empty line is exactly `什麼是 {topic}？`. If web research was required, list sources separately after the script without inserting them into the narration.
