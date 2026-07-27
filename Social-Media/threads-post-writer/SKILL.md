---
name: threads-post-writer
description: Use when a user gives a short topic and asks for a fact-checked, multi-post Threads series in Traditional Chinese, especially for current AI, technology, research papers, products, or trends that require web research and coherent continuity across posts. For paper-reading topics, focus the publishable copy on the paper itself, omit discovery or hosting platforms, and place unique, semantically matched original paper figures below every post. Also use when running the bundled Codex CLI writer for this workflow.
---

# Threads Post Writer

## Overview

Turn a short topic into a researched, source-grounded Threads series that reads as one continuous argument. Build the narrative spine before drafting any individual post.

## Python entry point

Run the bundled wrapper when the user wants the complete research-and-writing workflow from Python:

```bash
python {SKILL_PATH}/scripts/write_threads.py "GPT-5.6" --output threads-output/gpt-5-6.md
```

Optionally constrain the article to one angle:

```bash
python {SKILL_PATH}/scripts/write_threads.py "GPT-5.6" --angle "為什麼重要" --output threads-output/gpt-5-6.md
```

Always add `--paper` when the topic is a paper. The wrapper also auto-detects common paper URLs, identifiers, and explicit `paper` or `論文` wording, but use the flag for a title that has no such signal:

```bash
python {SKILL_PATH}/scripts/write_threads.py "<paper title or URL>" --paper --output threads-output/paper-thread.md
```

The wrapper must keep `gpt-5.6-sol` and `model_reasoning_effort="high"` fixed. Do not add model or reasoning override flags. Query the authenticated Codex model catalog before generation, and stop without fallback if that exact model or effort is unavailable. Run Codex with `workspace-write` and preserve the user's Codex configuration; do not pass `--ignore-user-config`, because Codex CLI 0.144.1 on Windows can otherwise start the effective sandbox as `read-only`. Require the output path to stay inside the selected working directory, scope the nested writable root to a dedicated output subdirectory, and refuse directories that already contain unrelated files. Have Codex write the Markdown file directly and run `validate.py`, then independently repeat the audit in the wrapper. Reject any extra top-level artifact created by the nested run. In paper mode, store figures in the sibling `<output-stem>-figures/` directory and run the validator with `--paper`. Do not use the final chat message as the article file.

On Windows, prefer executing paper research and figure extraction directly in the current Codex task when its authorized tools can write the workspace. If the nested wrapper reports `CreateProcessAsUserW failed: 5`, treat it as a Windows sandbox runtime failure: do not weaken the sandbox or invent substitutes. Continue directly only within the current task's existing permissions; otherwise report the blocker.

## Non-negotiable rules

- Browse the web for current or unstable facts. Do not answer from memory when facts may have changed.
- Prefer primary sources: official announcements, documentation, system cards, original papers, repositories, and named research institutions.
- Separate sourced facts, inference, and rumor. Never present inference or rumor as confirmed fact.
- Verify every benchmark, date, price, limit, model name, and quoted capability against a primary source.
- If the topic is ambiguous or has no reliable evidence, stop and explain what is unverified instead of inventing a release or specification.
- Keep the claim ledger internal. Do not put URLs, citations, a source ledger, review notes, or a `核對來源` section in the generated Markdown.
- Treat paper discovery and hosting pages as research infrastructure only. Never make Hugging Face, arXiv, OpenReview, Semantic Scholar, Papers with Code, ResearchGate, rankings, upvotes, or download location part of publishable paper copy.
- Activate paper mode whenever the requested topic is a paper. Speak directly about the paper's question, method, evidence, limits, and implications.
- When the topic has a verified, stable name, put that exact core name in the first non-empty prose line and position its concrete innovation there. Do not make the reader wait through generic background before learning what the series is about.
- Write the complete narrative before inserting post separators. Do not draft through JSON, sentence arrays, per-post forms, or other fill-in-the-box structures.

## Workflow

### 1. Resolve and research the topic

1. Identify the exact entity, version, date, and likely ambiguity behind the user's short topic.
2. Search the current web. For OpenAI products, use official OpenAI sources unless the user requests broader coverage.
3. Build an internal claim ledger with:
   - claim
   - evidence status: confirmed, inference, or rumor
   - source URL and publication date
   - wording strength allowed by the evidence
   Never write this ledger or its URLs into the generated Markdown.
4. Require a primary source for every important number. Seek a second source for the central conclusion when one exists.
5. Choose one angle. Do not turn the series into a catalogue of unrelated features.
6. For a paper topic, trace any discovery URL to the primary paper, read the relevant full text and captions, and keep the discovery route out of the article.

### 2. Build one narrative spine

Write one sentence that states the conclusion the whole series will prove. Then map four consecutive reasoning jobs:

1. **Post 1 — significance:** open with the approved naming-positioning line, then establish the current assumption, tension, and main finding.
2. **Post 2 — bottleneck:** explain the existing approach and the problem it cannot solve.
3. **Post 3 — mechanism:** answer that bottleneck with the new architecture, method, or operating principle.
4. **Post 4 — consequence:** explain verified results, limits, applications, and the final judgment.

Before drafting, record the last idea of each post and the first idea of the next. They must form a causal bridge, not four neighboring summaries.

### 3. Lock the naming-positioning Hook

When the subject has a verified method, system, model, product, project, or paper name, use a naming-positioning Hook as the default first non-empty prose line:

```text
核心名稱：具體定位＋核心創新
```

This is the first prose sentence, not a Markdown heading. For a paper, use the paper's own method or system name, not its hosting platform, discovery page, full bibliographic title, field category, or benchmark result. The text after the colon must tell the reader both what the subject is and what concretely makes it different. Prefer the operating idea over an unsupported superlative.

Approved pattern:

```text
SpectraReward：讓 LLM「讀回 Prompt」的全新圖片評估方法
```

Use the second line to unpack the contrast, mechanism, or consequence promised by the Hook. Put field background after this positioning. Do not open with a generic field observation, a scene-setting question, vague suspense, or a benchmark headline by default. Use result-first only when the user explicitly requests it, no stable core name exists, or naming the entity first would be misleading; record the reason internally and still identify the subject in the first line.

Run this **Hook Gate** before drafting the remaining prose:

- The exact core name appears in the first non-empty prose line.
- The same line states a recognizable category or job and one concrete differentiator.
- A stranger can identify the subject and its new idea without reading the second line.
- The claim remains accurate after removing hype words such as `突破性`, `革命性`, or `更強大`.
- The second line develops the first line instead of restarting with broad background.

Reject and rewrite the opening if the name first appears on line 2 or later, if the first line could introduce many unrelated topics, or if the strongest paper-specific positioning is delayed. A strong Hook is compatible with a neutral engineering voice; the ban on engagement bait is not a ban on immediate, specific positioning.

### 4. Draft prose-first

Draft all four posts as one continuous article in a single pass. Insert `---` separators only after the argument reads naturally from beginning to end.

Use these continuity constraints:

- Let each later post inherit an unresolved concept from the preceding post.
- Do not reintroduce the topic at the start of every post.
- Do not repeat the same background, benchmark, conclusion, or definition.
- Add at least one new piece of information in every post.
- Make the final post resolve the expectation created by the first.
- Keep each post independently understandable without making it sound independent from the series.

### 5. Match the target voice

- Use Traditional Chinese with necessary English model names and technical abbreviations.
- Prefer neutral, compact, engineering-oriented explanation over excitement or personal storytelling.
- Put one semantic sentence on each line.
- Use concrete scenarios or analogies to translate abstract mechanisms.
- Preserve verified numbers and benchmarks when they materially support the argument.
- Prefer decisive explanatory endings over calls to action.
- Avoid emoji, hashtags, engagement bait, numbered post labels, and direct reader address.
- Do not put a period at the end of a line unless it is required inside an English title or abbreviation.
- Treat these as editing targets, not validation gates: about 300–500 Chinese characters for the first post and 220–360 for each later post, usually 7–12 lines per post.

### 6. Run a continuity review

Read only the final line of each post followed by the first line of the next. Rewrite any boundary that feels like a reset.

Then read the entire series without separators and check:

- the argument has one thesis
- the order is causal rather than topical
- no paragraph can be moved elsewhere without weakening the logic
- the fourth post answers the first post
- every factual claim matches the claim ledger

### 7. Lock the conclusion

Run this **Conclusion Gate** on the final prose before inserting paper figures. The fourth Post's last 1–2 prose lines must turn the evidence and limits into a bounded verdict, not merely recap benefits, list conditions, or gesture toward future value.

Use a structure like this only when it fits the evidence:

```text
核心名稱不會取代 X，但在 Y 這件事上，它改變／證明／取代了 Z
```

Example:

```text
SpectraReward 不會取代美感或安全評估，但在圖片是否忠實完成 Prompt 這件事上，它把評估訊號直接對準生成目標
```

Run the gate in this order:

- 先讀第一篇前兩個正文行，再讀第四篇最後兩個正文行。The ending must resolve the opening's promise or tension and state why the reader should update their view.
- State what the subject changes, proves, or replaces and where that claim stops. Decisive does not mean absolute; match the verdict's strength to the claim ledger.
- 限制不能取代結論。Move a list of caveats earlier, or integrate the decisive boundary into the verdict itself.
- Add no new benchmark, evidence, topic, or unsupported implication in the verdict.
- 移除核心名稱，或換成另一個方法；if the ending still works unchanged, it is too generic and must be rewritten.
- 最後一個正文行本身要包含核心名稱或只有這個主題才成立的機制；不能只靠前一行命名，再用代名詞收在泛用判斷.
- Reject endings that rely only on `值得關注`, `值得延伸`, `提供一條路線`, `未來可期`, `開啟更多可能`, or similar future-value language.
- End on the verdict, not a call to action, engagement question, or trailing disclaimer.

In paper mode, apply this gate to the final prose lines before the first image in Post 4. Figures may follow the verdict, but no prose may follow the first figure.

### 8. In paper mode, freeze prose before mapping figures

Treat each `---`-separated Post as the paragraph unit for figure placement.

1. Freeze the fact-checked prose after the continuity review. Do not add, remove, or redirect discussion to accommodate available figures.
2. Inventory every numbered, content-bearing Figure in the primary paper file, including appendix Figures in the same paper. Exclude tables, equations, logos, decorative assets, author photos, web thumbnails, and screenshots of discovery or hosting platforms.
3. Keep an internal figure ledger containing the Figure number, full caption, section, local asset path, content hash, and assigned Post. Do not publish the ledger.
4. Preserve each composite multi-panel Figure as one image. Do not split panels merely to create more attachments.
5. Assign every inventoried Figure exactly once to the Post whose already-written content best matches its caption and section. Give semantic fit priority over paper order, and never reuse, rename-copy, fabricate, or force an unrelated image.
6. Place one or more assigned figures immediately below the prose of each Post. Put no prose after the first image in that Post. Use a `Figure N：short caption` alt text and a local relative Markdown path. Put rasterized PNG, JPEG, or WebP files directly in `<output-stem>-figures/` with `figure-01` style names.
7. Confirm that every Post has at least one figure, every inventoried Figure appears once, and every file hash is unique. If all three conditions cannot hold without changing the prose, stop and explain the limitation instead of producing publishable Markdown.

### 9. Run the text-policy audit

Save the draft as Markdown and run:

```bash
python {SKILL_PATH}/validate.py <draft.md>
```

For a paper draft, run:

```bash
python {SKILL_PATH}/validate.py <draft.md> --paper
```

The base validator audits blacklist and whitelist terms, four-Post structure, URLs, DOI and citation markers, Markdown links, and obsolete JSON input. Paper mode additionally rejects named paper-hosting platforms, missing per-Post figures, invalid alt text, remote or missing assets, files outside the required figure directory, unsupported or corrupt images, unreferenced figure-directory entries, prose placed after an image, and duplicate paths or file content. It cannot prove semantic relevance or that the primary paper was inventoried completely; verify those two properties against the internal figure ledger.

Treat `to_preview_md.py` as a deprecated alias for the same validator arguments. It does not accept the old preview filename argument, convert JSON, or create a preview file.

## Output contract

Return publishable prose first, separated only by `---`:

```markdown
[Post 1]

---

[Post 2]

---

[Post 3]

---

[Post 4]
```

In paper mode, append the assigned local image lines after each Post's prose and before its separator:

```markdown
[Post prose]

![Figure 1：short caption](paper-thread-figures/figure-01.png)

---
```

End ordinary Markdown at the final prose line of Post 4; end paper-mode Markdown at the final assigned image line of Post 4. Do not append sources, remote URLs, citations, uncertainty notes, review notes, or any other metadata. Keep research evidence in the working process only. If evidence is incomplete or sources conflict, stop and explain the limitation outside the article instead of producing a publishable file.

## Failure handling

- **Unverified name or release:** report that no official confirmation was found; do not create a product introduction.
- **Conflicting sources:** prefer the newest primary source; if the conflict affects the conclusion, stop without producing the article.
- **Only secondary coverage exists:** lower the wording strength and identify the limitation.
- **Too little material for four posts:** ask for a narrower angle or write fewer posts only when the user explicitly agrees.
- **Insufficient or inaccessible paper figures:** stop if there are fewer than four usable original Figures, if any inventoried Figure lacks an honest semantic match, or if the complete Figure inventory cannot be verified. Never duplicate or substitute a platform screenshot.
- **Windows nested sandbox cannot start tools:** if `CreateProcessAsUserW failed: 5` occurs, stop the wrapper. Continue in the current task only when its existing authorization already permits the same workspace-local work; never switch the nested run to unrestricted access automatically.

## Common mistakes

- Writing four self-contained mini-articles instead of one argument
- Treating headings or JSON fields as a substitute for transitions
- Opening with generic field background and postponing the core name or contribution until line 2 or later
- Treating a neutral voice as a reason to avoid a concrete Hook, or defaulting to a benchmark/result-first opening when a stable core name exists
- Ending with a benefit recap, a list of conditions, or generic future-value language instead of a bounded verdict that pays off the opening
- Adding limitations after the verdict until the last line becomes a disclaimer rather than the conclusion
- Repeating the product introduction in every post
- Using a benchmark without its evaluation conditions
- Leaking the internal claim ledger, URLs, citations, or a source section into the publishable Markdown
- Leading with where a paper was found instead of what the paper contributes
- Selecting figures before the prose is final, then bending the argument around the available images
- Reusing one image under multiple Posts or treating renamed copies and split panels as distinct Figures
- Adding vague viral bait, emoji, or comment prompts that conflict with the target voice
