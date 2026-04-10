---
name: editorial-pipeline-en
description: A six-stage editorial quality control pipeline (3 reviews + 3 proofreadings) for blog posts, newsletters, technical articles, and long-form content. Each reviewer role MUST be dispatched as an independent subagent to ensure uncontaminated perspectives. Use when you need rigorous, multi-pass quality assurance on written articles before publication.
---

# Editorial Pipeline — Article Quality Control

> ⚠️ **Core Principle: Each reviewer role = an independent subagent**
> Every reviewer must be invoked as a separate subagent — never have the same agent play multiple roles.
> This guarantees each review pass has a truly independent perspective, uncontaminated by previous rounds.

---

## When to Use

- Before publishing blog posts, technical tutorials, or newsletters
- Before submitting long-form essays, RFCs, product announcements, or brand copy
- Any high-visibility content where argument rigor and precise language matter

---

## Process Overview

```
Draft produced
      │
      ▼
[THREE-REVIEW STAGE] — Content-level assessment
      ├── Review 1 subagent: Structure & completeness
      ├── Review 2 subagent: Logic, accuracy & depth
      └── Review 3 subagent: Final verdict & publish readiness
      │
      ▼ (each round: feedback → revise → next round)
      │
[THREE-PROOFREAD STAGE] — Detail-level correction
      ├── Proof 1 subagent: Line-by-line scan for errors
      ├── Proof 2 subagent: Verify corrections, catch new issues
      └── Proof 3 subagent: Author cold-read, final sign-off
      │
      ▼
Published

```

---

## Three-Review Specs

### Review 1 subagent — `content-first-reviewer`

**Role:** Gate basic quality. Prevent obvious holes from reaching later stages.

**Checklist:**
- [ ] Argument is clear with a distinct thesis statement
- [ ] Structure is complete: intro, body, conclusion
- [ ] Appropriate for the target audience's knowledge level and expectations
- [ ] No filler sentences, AI boilerplate, or excessive hedging language

**Output format:**
```
Review 1 Result (content-first-reviewer)
Status: [Pass / Revise]
Issues:
  - [Critical] ...
  - [Suggestion] ...
Revision instructions: ...
```

---

### Review 2 subagent — `content-deep-reviewer`

**Prerequisite:** Only start after Review 1 passes.

**Role:** Deep-dive into logical consistency, factual accuracy, and potential risks.

**Checklist:**
- [ ] Claims are backed by evidence; no fabricated data or unsupported assertions
- [ ] Sections flow logically with no internal contradictions
- [ ] Every paragraph advances the core argument; no tangents
- [ ] Citations, data, and sources are credible and verifiable
- [ ] Tone and stance are consistent throughout (no formal/informal mixing)
- [ ] No potential brand, legal, or copyright risks

**Output format:**
```
Review 2 Result (content-deep-reviewer)
Status: [Pass / Revise / Needs structural discussion]
Major issues: ...
Minor issues: ...
Strengths (worth keeping): ...
```

---

### Review 3 subagent — `content-chief-reviewer`

**Prerequisite:** Only start after Review 2 passes.

**Role:** Final verdict on publishability. Do not re-litigate details already covered; focus on big-picture judgment.

**Checklist:**
- [ ] Voice is consistent throughout — reads like a single author
- [ ] Headline promise is fully delivered in the body (no clickbait)
- [ ] Achieves the intended reader action (understanding, persuasion, click, subscribe)
- [ ] Ending lands with impact rather than trailing off
- [ ] Safe to publish (no legal, brand, or copyright concerns)

**Output format:**
```
Review 3 Verdict (content-chief-reviewer)
Decision: [Approved / Revise / Hold]
Reasoning: ...
Conditions (if any): ...
```

---

## Three-Proofread Specs

> Proofreading applies only to content that has passed all three reviews. Focus on surface errors, not structural issues.

### Proof 1 subagent — `proofreader-first`

**Role:** Scan paragraph by paragraph against the final revised draft.

**Checklist:**
- [ ] Spelling errors, homophones, missing words
- [ ] Punctuation used correctly (periods, commas, quotation marks, em-dashes)
- [ ] Heading hierarchy (H1/H2/H3) is correct and consistent
- [ ] Link anchor text matches its destination
- [ ] Number formatting is consistent (commas, units, decimal style)

**Output format:**
```
Proof 1 Report (proofreader-first)
Error list (with paragraph or line reference):
  Para 3: "occured" → "occurred"
  ...
```

---

### Proof 2 subagent — `proofreader-second`

**Prerequisite:** Proof 1 corrections have been applied.

**Role:** Independently verify that Proof 1 fixes were applied correctly and catch anything missed.

**Checklist:**
- [ ] All issues flagged in Proof 1 have been resolved
- [ ] Fixes themselves are correct (no new errors introduced by the edit)
- [ ] Any new detail issues not caught by Proof 1

**Output format:**
```
Proof 2 Report (proofreader-second)
Proof 1 fix confirmation: [All correct / X items incorrect]
Incorrect items: ...
Newly found issues: ...
```

---

### Proof 3 subagent — `proofreader-final`

**Prerequisite:** All Proof 2 items resolved.

**Role:** Final read-through as the author/publisher, simulating the reader experience.

**Checklist:**
- [ ] Cold read from start to finish — prose flows naturally
- [ ] All issues from previous rounds are resolved
- [ ] Author, date, tags, and meta description are correct
- [ ] Formatting (Markdown/HTML/rich text) matches the target publishing platform

**Output format:**
```
Proof 3 Result (proofreader-final)
Status: [Final — cleared for publication / Pending items]
Pending (if any): ...
Sign-off: proofreader-final @ {date}
```

---

## How to Dispatch Subagents

Every review and proofread pass must be dispatched via `runSubagent` / Task tool. **Do not role-play multiple reviewers within the same agent session.**

```
Example (Review 1):
runSubagent(
  agentName: "content-first-reviewer",
  prompt: """
  You are the first-pass reviewer. Below is the article draft:

  [paste full article text]

  Complete the Review 1 checklist and return your report
  in the 'Review 1 Result' format.
  """
)
```

Each subagent prompt must clearly state:
1. Its role and responsibilities for this pass
2. The previous round's findings (if any)
3. The full current article text
4. The required output format

---

## Revision Loop

If any round returns "Revise", follow this loop:

```
Revise → author edits → re-submit to same round (not from the top)
         (if edits are major, restart from Review 1)
```

**Scope judgement:**
- Changes < 20% of content → re-run from the round that returned Revise
- Changes ≥ 20% of structure → restart from Review 1

---

## Quick Reference

| Stage | Subagent Name | Focus |
|-------|--------------|-------|
| Review 1 | `content-first-reviewer` | Structure, completeness, basic quality |
| Review 2 | `content-deep-reviewer` | Logic, accuracy, depth, risks |
| Review 3 | `content-chief-reviewer` | Big-picture judgment, publish verdict |
| Proof 1 | `proofreader-first` | Line-by-line error scan |
| Proof 2 | `proofreader-second` | Verify fixes, catch new errors |
| Proof 3 | `proofreader-final` | Author cold-read, final sign-off |
