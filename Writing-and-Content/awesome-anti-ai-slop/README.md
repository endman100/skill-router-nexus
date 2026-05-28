# Awesome Anti AI Slop

> A collection of tools for removing AI slop.

[![Awesome](https://awesome.re/badge.svg)](https://awesome.re)
![Last Updated](https://img.shields.io/badge/updated-2026--05--27-blue)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

[中文版 README](./README_CN.md)

## What is AI slop?

**AI slop** is the recognizable low-quality residue of AI-generated work:

- Hollow, templated, overly smooth prose;
- Mechanical connectors like "not only… but also…", "in conclusion", "it is worth noting that";
- Lots of technically correct but insight-free generalities;
- Code that looks complete but lacks edge-case handling, tests, or error handling;
- Bulk low-quality changes in PRs;
- Cookie-cutter cards, gradients, centered heroes, and meaningless animations in UI;
- Design language, typography, spacing, and information hierarchy lacking judgment.

Projects that only sell "undetectable" results are excluded.

## Selection Criteria

Inclusion criteria:

1. **Open-source and directly usable** — skill, prompt, CLI, app, GitHub Action, linter, or rule set.
2. **Delivers real quality improvement** — text, code, PRs, UI, or design; not a thin wrapper around a synonym replacement API.
3. **Has verifiable value** — star count, forks, documented use cases, or implementation quality; at least one.
4. **Not a marketing shell** — no source code, no rule set, detector bypass as the main pitch: not included.
5. **Integrates into standard workflows** — Claude Code, Codex, Cursor, CI, pre-commit, or team documentation.

> Star counts reflect the time of curation and will change.

## Contents

- [Best Picks](#best-picks)
- [Starter Stacks](#starter-stacks)
- [Text & Writing](#text--writing)
- [Chinese Writing](#chinese-writing)
- [Academic Writing](#academic-writing)
- [Frontend, UI & Design Taste](#frontend-ui--design-taste)
- [Code, PR & Engineering Slop](#code-pr--engineering-slop)
- [Apps, CLIs & Workbenches](#apps-clis--workbenches)
- [Directories & Meta Lists](#directories--meta-lists)
- [Niche / Experimental](#niche--experimental)
- [How to Evaluate an Anti-Slop Tool](#how-to-evaluate-an-anti-slop-tool)
- [Contributing](#contributing)
- [License](#license)

## Best Picks

| Project | Stars | Best for | Why it matters |
|---|---:|---|---|
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | [![Stars](https://img.shields.io/github/stars/pbakaus/impeccable?style=social)](https://github.com/pbakaus/impeccable) | Frontend / UI / design anti-slop | Fixes the template-gradient-hero look AI reliably generates. Most-starred project in this space. |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | [![Stars](https://img.shields.io/github/stars/Leonxlnx/taste-skill?style=social)](https://github.com/Leonxlnx/taste-skill) | AI-built frontend taste | Skill framework that enforces layout, typography, motion, and spacing constraints on AI-built UIs. Supports Codex, Cursor, Claude Code. |
| [blader/humanizer](https://github.com/blader/humanizer) | [![Stars](https://img.shields.io/github/stars/blader/humanizer?style=social)](https://github.com/blader/humanizer) | English writing humanizer | English writing de-slopper. Articles, docs, emails, copy. |
| [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | [![Stars](https://img.shields.io/github/stars/Imbad0202/academic-research-skills?style=social)](https://github.com/Imbad0202/academic-research-skills) | Research / academic workflow | Academic toolkit covering research quality, structure, and writing — beyond surface humanizing. |
| [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) | [![Stars](https://img.shields.io/github/stars/op7418/Humanizer-zh?style=social)](https://github.com/op7418/Humanizer-zh) | Chinese writing | Chinese de-slopper. Covers articles, academic drafts, WeChat posts, and business copy. |
| [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | [![Stars](https://img.shields.io/github/stars/hardikpandya/stop-slop?style=social)](https://github.com/hardikpandya/stop-slop) | Prompt rules / prose cleanup | Rules-based. Good starting point for a custom system prompt or Claude Project instruction file. |
| [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | [![Stars](https://img.shields.io/github/stars/conorbronsdon/avoid-ai-writing?style=social)](https://github.com/conorbronsdon/avoid-ai-writing) | Detect + rewrite workflow | Two modes: detect AI patterns, then rewrite. Useful for content teams running drafts through a review pass. |
| [peakoss/anti-slop](https://github.com/peakoss/anti-slop) | [![Stars](https://img.shields.io/github/stars/peakoss/anti-slop?style=social)](https://github.com/peakoss/anti-slop) | GitHub PR quality gate | GitHub Action that flags or closes low-quality AI-generated PRs before they land. |
| [mshumer/unslop](https://github.com/mshumer/unslop) | [![Stars](https://img.shields.io/github/stars/mshumer/unslop?style=social)](https://github.com/mshumer/unslop) | Custom anti-slop instructions | Reads samples of your writing or brand voice and generates a custom instruction file from the patterns it finds. |
| [brandonwise/humanizer](https://github.com/brandonwise/humanizer) | [![Stars](https://img.shields.io/github/stars/brandonwise/humanizer?style=social)](https://github.com/brandonwise/humanizer) | CLI / local audit | Low stars, but ships scoring, analysis, diff, and suggestions as a local workflow rather than a cloud API. |

## Starter Stacks

### Chinese Writing

- [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) — Primary Chinese de-slopper.
- [cangtianhuang/humanizer-academic-zh](https://github.com/cangtianhuang/humanizer-academic-zh) — Dedicated to Chinese academic writing.
- [marswjf/stop-slop-zh](https://github.com/marswjf/stop-slop-zh) — Bilingual (Chinese/English) rules-based de-slop skill.
- [1-SKILL/shuorenhua](https://github.com/1-SKILL/shuorenhua) — Small project focused on making Chinese "sound human".

### English Blog / Docs / Product Copy

- [blader/humanizer](https://github.com/blader/humanizer) — Primary humanizer.
- [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) — Rule baseline.
- [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) — Detect + rewrite.
- [jalaalrd/anti-ai-slop-writing](https://github.com/jalaalrd/anti-ai-slop-writing) — Lightweight anti-slop writing prompt.

### Frontend / UI / Product Design

- [pbakaus/impeccable](https://github.com/pbakaus/impeccable) — Frontend/UI anti-slop.
- [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) — AI-built frontend taste framework.
- [mshumer/unslop](https://github.com/mshumer/unslop) — Generate team-specific anti-slop instructions.
- [Wholiver/swiftui-design-skill](https://github.com/Wholiver/swiftui-design-skill) — SwiftUI design direction.
- [Hacksore/oghunt](https://github.com/Hacksore/oghunt) — Remove AI noise from Product Hunt feed.

### Code / PR / Team Governance

- [peakoss/anti-slop](https://github.com/peakoss/anti-slop) — GitHub Action.
- [scanaislop/aislop](https://github.com/scanaislop/aislop) — AI code quality gate / hook / MCP.
- [JordanGunn/agent-slop-lint](https://github.com/JordanGunn/agent-slop-lint) — Agentic coding linter.
- [yuvrajangadsingh/vibecheck](https://github.com/yuvrajangadsingh/vibecheck) — JS/TS/Python slop lint.
- [HugoLopes45/llmstrip](https://github.com/HugoLopes45/llmstrip) — Lightweight cleanup of prose / comments / commits.

## Text & Writing

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [blader/humanizer](https://github.com/blader/humanizer) | [![Stars](https://img.shields.io/github/stars/blader/humanizer?style=social)](https://github.com/blader/humanizer) | Skill | English writing de-slopper. Covers documentation, blogs, and emails. |
| [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | [![Stars](https://img.shields.io/github/stars/hardikpandya/stop-slop?style=social)](https://github.com/hardikpandya/stop-slop) | Skill / rules | Identifies banned phrases, structural templates, and sentence-level AI patterns. |
| [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | [![Stars](https://img.shields.io/github/stars/conorbronsdon/avoid-ai-writing?style=social)](https://github.com/conorbronsdon/avoid-ai-writing) | Skill / workflow | Detect and Rewrite modes, for content teams. |
| [jalaalrd/anti-ai-slop-writing](https://github.com/jalaalrd/anti-ai-slop-writing) | [![Stars](https://img.shields.io/github/stars/jalaalrd/anti-ai-slop-writing?style=social)](https://github.com/jalaalrd/anti-ai-slop-writing) | Prompt | Lightweight rule pack targeting vocabulary, structure, punctuation, and formatting. |
| [coderjatin/anti-slop-writing](https://github.com/coderjatin/anti-slop-writing) | [![Stars](https://img.shields.io/github/stars/coderjatin/anti-slop-writing?style=social)](https://github.com/coderjatin/anti-slop-writing) | Prompt | Compatible with Claude Code, Gemini CLI, Codex CLI, Copilot, Cursor, etc. |
| [stephenturner/skill-deslop](https://github.com/stephenturner/skill-deslop) | [![Stars](https://img.shields.io/github/stars/stephenturner/skill-deslop?style=social)](https://github.com/stephenturner/skill-deslop) | Skill | De-slops scientific and technical writing; targets formulaic structure, filler, and false agency. |
| [rankgnar/deslop](https://github.com/rankgnar/deslop) | [![Stars](https://img.shields.io/github/stars/rankgnar/deslop?style=social)](https://github.com/rankgnar/deslop) | CLI | Detects and removes buzzwords, false profundity, and hollow transitions. |
| [AUAggy/deslop](https://github.com/AUAggy/deslop) | [![Stars](https://img.shields.io/github/stars/AUAggy/deslop?style=social)](https://github.com/AUAggy/deslop) | VS Code / rewrite | Rewrites selected text under strict rules without generating new content. |
| [gabelul/slopbuster](https://github.com/gabelul/slopbuster) | [![Stars](https://img.shields.io/github/stars/gabelul/slopbuster?style=social)](https://github.com/gabelul/slopbuster) | Audit / rules | Audits prose, code, and academic writing; includes multi-mode audit approaches. |
| [ksanyok/TextHumanize](https://github.com/ksanyok/TextHumanize) | [![Stars](https://img.shields.io/github/stars/ksanyok/TextHumanize?style=social)](https://github.com/ksanyok/TextHumanize) | Library | Offline multilingual text normalization library; unrelated to detector evasion. |
| [HugoLopes45/llmstrip](https://github.com/HugoLopes45/llmstrip) | [![Stars](https://img.shields.io/github/stars/HugoLopes45/llmstrip?style=social)](https://github.com/HugoLopes45/llmstrip) | Rust CLI | Handles LLM traces in prose, code comments, and commit messages. |
| [avectats7/anti-ai-writing](https://github.com/avectats7/anti-ai-writing) | [![Stars](https://img.shields.io/github/stars/avectats7/anti-ai-writing?style=social)](https://github.com/avectats7/anti-ai-writing) | Prompt | English/Spanish rule pack targeting banned words, phrases, and structures. |

## Chinese Writing

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) | [![Stars](https://img.shields.io/github/stars/op7418/Humanizer-zh?style=social)](https://github.com/op7418/Humanizer-zh) | Skill | Chinese de-slopper. Covers drafts, business copy, and academic papers. |
| [cangtianhuang/humanizer-academic-zh](https://github.com/cangtianhuang/humanizer-academic-zh) | [![Stars](https://img.shields.io/github/stars/cangtianhuang/humanizer-academic-zh?style=social)](https://github.com/cangtianhuang/humanizer-academic-zh) | Prompt / skill | Removes AI traces from Chinese academic writing. |
| [marswjf/stop-slop-zh](https://github.com/marswjf/stop-slop-zh) | [![Stars](https://img.shields.io/github/stars/marswjf/stop-slop-zh?style=social)](https://github.com/marswjf/stop-slop-zh) | Skill / prompt | Bilingual (Chinese/English) de-slop skill; supports Claude Code, OpenClaw, Codex CLI, Cursor/Windsurf, etc. |
| [shyuan/writing-humanizer](https://github.com/shyuan/writing-humanizer) | [![Stars](https://img.shields.io/github/stars/shyuan/writing-humanizer?style=social)](https://github.com/shyuan/writing-humanizer) | Plugin / skill | Traditional Chinese (Taiwan) writing humanizer. |
| [1-SKILL/shuorenhua](https://github.com/1-SKILL/shuorenhua) | [![Stars](https://img.shields.io/github/stars/1-SKILL/shuorenhua?style=social)](https://github.com/1-SKILL/shuorenhua) | Skill | Chinese "speak like a human" rewriter; niche, narrow scope. |

## Academic Writing

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | [![Stars](https://img.shields.io/github/stars/Imbad0202/academic-research-skills?style=social)](https://github.com/Imbad0202/academic-research-skills) | Skill collection | Academic research toolkit: research quality, paper writing, and style calibration. |
| [cangtianhuang/humanizer-academic-zh](https://github.com/cangtianhuang/humanizer-academic-zh) | [![Stars](https://img.shields.io/github/stars/cangtianhuang/humanizer-academic-zh?style=social)](https://github.com/cangtianhuang/humanizer-academic-zh) | Chinese academic | Anti-AI-trace prompt/skill dedicated to Chinese academic writing. |
| [stephenturner/skill-deslop](https://github.com/stephenturner/skill-deslop) | [![Stars](https://img.shields.io/github/stars/stephenturner/skill-deslop?style=social)](https://github.com/stephenturner/skill-deslop) | Scientific / technical | De-slops scientific writing, technical blogs, and research communication. |
| [gabelul/slopbuster](https://github.com/gabelul/slopbuster) | [![Stars](https://img.shields.io/github/stars/gabelul/slopbuster?style=social)](https://github.com/gabelul/slopbuster) | Audit | Prose/code/academic writing audit and scoring approach. |

## Frontend, UI & Design Taste

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | [![Stars](https://img.shields.io/github/stars/pbakaus/impeccable?style=social)](https://github.com/pbakaus/impeccable) | Frontend / UI skill | Frontend/UI/design anti-slop for the templated look of AI-generated web pages. |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | [![Stars](https://img.shields.io/github/stars/Leonxlnx/taste-skill?style=social)](https://github.com/Leonxlnx/taste-skill) | Frontend skill framework | Gives your AI good taste. Covers layout, typography, motion, spacing, design system, redesign audit, and image-to-code constraints. |
| [mshumer/unslop](https://github.com/mshumer/unslop) | [![Stars](https://img.shields.io/github/stars/mshumer/unslop?style=social)](https://github.com/mshumer/unslop) | Instruction generator | Extracts the model's default patterns from text or visual samples and generates a reusable instruction file. |
| [Wholiver/swiftui-design-skill](https://github.com/Wholiver/swiftui-design-skill) | [![Stars](https://img.shields.io/github/stars/Wholiver/swiftui-design-skill?style=social)](https://github.com/Wholiver/swiftui-design-skill) | SwiftUI design skill | SwiftUI design direction, mobile UI quality. |
| [Hacksore/oghunt](https://github.com/Hacksore/oghunt) | [![Stars](https://img.shields.io/github/stars/Hacksore/oghunt?style=social)](https://github.com/Hacksore/oghunt) | Product Hunt filter | Removes AI listings from the Product Hunt feed. |

### Taste Skill install example

```bash
npx skills add https://github.com/Leonxlnx/taste-skill
npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"
```

For AI-generated interface problems. Text quality issues need a different tool.

## Code, PR & Engineering Slop

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [peakoss/anti-slop](https://github.com/peakoss/anti-slop) | [![Stars](https://img.shields.io/github/stars/peakoss/anti-slop?style=social)](https://github.com/peakoss/anti-slop) | GitHub Action | Detects and closes low-quality or AI slop PRs. |
| [JordanGunn/agent-slop-lint](https://github.com/JordanGunn/agent-slop-lint) | [![Stars](https://img.shields.io/github/stars/JordanGunn/agent-slop-lint?style=social)](https://github.com/JordanGunn/agent-slop-lint) | Linter | Language-agnostic code quality linter aimed at agentic coding. |
| [scanaislop/aislop](https://github.com/scanaislop/aislop) | [![Stars](https://img.shields.io/github/stars/scanaislop/aislop?style=social)](https://github.com/scanaislop/aislop) | Hook / MCP / quality gate | AI code quality gate for Claude Code, Cursor, and Codex. |
| [yuvrajangadsingh/vibecheck](https://github.com/yuvrajangadsingh/vibecheck) | [![Stars](https://img.shields.io/github/stars/yuvrajangadsingh/vibecheck?style=social)](https://github.com/yuvrajangadsingh/vibecheck) | JS/TS/Python linter | ESLint-style AI slop detection. |
| [adamcharnock/deslop](https://github.com/adamcharnock/deslop) | [![Stars](https://img.shields.io/github/stars/adamcharnock/deslop?style=social)](https://github.com/adamcharnock/deslop) | pre-commit prose lint | Checks for AI writing patterns in docs and prose before committing. |
| [HugoLopes45/llmstrip](https://github.com/HugoLopes45/llmstrip) | [![Stars](https://img.shields.io/github/stars/HugoLopes45/llmstrip?style=social)](https://github.com/HugoLopes45/llmstrip) | CLI | Cleans up LLM traces in code comments, commit messages, and prose. |

## Apps, CLIs & Workbenches

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [lynote-ai/humanize-text](https://github.com/lynote-ai/humanize-text) | [![Stars](https://img.shields.io/github/stars/lynote-ai/humanize-text?style=social)](https://github.com/lynote-ai/humanize-text) | App | App-style AI text humanizer with high traction. Works best as an editing aid. |
| [DadaNanjesha/AI-Text-Humanizer-App](https://github.com/DadaNanjesha/AI-Text-Humanizer-App) | [![Stars](https://img.shields.io/github/stars/DadaNanjesha/AI-Text-Humanizer-App?style=social)](https://github.com/DadaNanjesha/AI-Text-Humanizer-App) | App | App for formal and academic-style rewriting. |
| [brandonwise/humanizer](https://github.com/brandonwise/humanizer) | [![Stars](https://img.shields.io/github/stars/brandonwise/humanizer?style=social)](https://github.com/brandonwise/humanizer) | CLI / OpenClaw skill | Local workflow: scoring, analysis, reporting, suggestions, scanning, diff. |
| [rudra496/StealthHumanizer](https://github.com/rudra496/StealthHumanizer) | [![Stars](https://img.shields.io/github/stars/rudra496/StealthHumanizer?style=social)](https://github.com/rudra496/StealthHumanizer) | App / multi-provider | Multi-provider, multi-level rewriting; "stealth/bypass"-oriented, use with caution. |
| [ZAYUVALYA/AI-Text-Humanizer](https://github.com/ZAYUVALYA/AI-Text-Humanizer) | [![Stars](https://img.shields.io/github/stars/ZAYUVALYA/AI-Text-Humanizer?style=social)](https://github.com/ZAYUVALYA/AI-Text-Humanizer) | App / paraphrasing | Context-aware paraphrasing; early stage. |
| [dixon2004/ai-humanizer](https://github.com/dixon2004/ai-humanizer) | [![Stars](https://img.shields.io/github/stars/dixon2004/ai-humanizer?style=social)](https://github.com/dixon2004/ai-humanizer) | Web/local app | Small Gemini-powered humanizer. |
| [puneethkotha/humanizer-workbench](https://github.com/puneethkotha/humanizer-workbench) | [![Stars](https://img.shields.io/github/stars/puneethkotha/humanizer-workbench?style=social)](https://github.com/puneethkotha/humanizer-workbench) | CLI / skill | Humanizer workbench; niche project. |
| [itsjwill/humanizer-x](https://github.com/itsjwill/humanizer-x) | [![Stars](https://img.shields.io/github/stars/itsjwill/humanizer-x?style=social)](https://github.com/itsjwill/humanizer-x) | Agent / workflow | 4-pass humanizer + voice agent; niche project. |

## Directories & Meta Lists

| Project / Topic | Stars | Notes |
|---|---:|---|
| [shannhk/avoid-slop](https://github.com/shannhk/avoid-slop) | [![Stars](https://img.shields.io/github/stars/shannhk/avoid-slop?style=social)](https://github.com/shannhk/avoid-slop) | Dedicated collection of anti-AI-slop tools for text, code, and design. |
| [GitHub Topic: ai-humanizer](https://github.com/topics/ai-humanizer) | - | Collection of text humanizer apps / skills / prompts. |
| [GitHub Topic: humanize-text](https://github.com/topics/humanize-text) | - | Narrower text humanizer topic. |
| [GitHub Topic: ai-slop](https://github.com/topics/ai-slop) | - | Broader AI slop covering PRs, code, UI, design, content noise, and more. |

## Niche / Experimental

Lower traction, niche scope, or heavy "bypass" marketing. Rules and implementations worth reading; outputs unreliable.

| Project | Stars | Notes |
|---|---:|---|
| [Aboudjem/humanizer-skill](https://github.com/Aboudjem/humanizer-skill) | [![Stars](https://img.shields.io/github/stars/Aboudjem/humanizer-skill?style=social)](https://github.com/Aboudjem/humanizer-skill) | Claude Code skill with multiple modes and voice profiles. |
| [Firdavs-coder/ai_humanizer](https://github.com/Firdavs-coder/ai_humanizer) | [![Stars](https://img.shields.io/github/stars/Firdavs-coder/ai_humanizer?style=social)](https://github.com/Firdavs-coder/ai_humanizer) | More of a prompt/model release. |
| [Hakku/finnish-humanizer](https://github.com/Hakku/finnish-humanizer) | [![Stars](https://img.shields.io/github/stars/Hakku/finnish-humanizer?style=social)](https://github.com/Hakku/finnish-humanizer) | Finnish-language humanizer. |
| [lguz/humanize-writing-skill](https://github.com/lguz/humanize-writing-skill) | [![Stars](https://img.shields.io/github/stars/lguz/humanize-writing-skill?style=social)](https://github.com/lguz/humanize-writing-skill) | Claude skill with a three-stage editing approach. |
| [199-biotechnologies/humanise-text-skill](https://github.com/199-biotechnologies/humanise-text-skill) | [![Stars](https://img.shields.io/github/stars/199-biotechnologies/humanise-text-skill?style=social)](https://github.com/199-biotechnologies/humanise-text-skill) | Claude Code skill; rule-list style. |
| [diaiq/claude-skill-humanizer](https://github.com/diaiq/claude-skill-humanizer) | [![Stars](https://img.shields.io/github/stars/diaiq/claude-skill-humanizer?style=social)](https://github.com/diaiq/claude-skill-humanizer) | Claude Code skill; watch out for detector-bypass promotion. |
| [imsv1301/unmask-ai](https://github.com/imsv1301/unmask-ai) | [![Stars](https://img.shields.io/github/stars/imsv1301/unmask-ai?style=social)](https://github.com/imsv1301/unmask-ai) | Detect + humanize wrapper. |
| [ofershap/ai-humanizer](https://github.com/ofershap/ai-humanizer) | [![Stars](https://img.shields.io/github/stars/ofershap/ai-humanizer?style=social)](https://github.com/ofershap/ai-humanizer) | Low-star project; promotion leans toward "undetectable" — use with caution. |
| [asazonov/deslop-codex](https://github.com/asazonov/deslop-codex) | [![Stars](https://img.shields.io/github/stars/asazonov/deslop-codex?style=social)](https://github.com/asazonov/deslop-codex) | Codex skill package; low traction. |

## How to Evaluate an Anti-Slop Tool

Checklist before adopting a tool:

1. **Synonym swap or structural rewrite?**  
   Low-quality humanizers rely on synonym swaps and injected typos. Meaningful improvement shows in structure, pacing, and specificity.

2. **Does it promise to bypass detectors?**  
   AI detectors have high false-positive rates and change constantly. Heavy "bypass Turnitin / GPTZero" promotion is a reliability warning.

3. **Does it alter your facts?**  
   Rewriting should preserve the original facts, position, and caveats. A tool that invents details or softens hard claims is unusable.

4. **Does it fit your actual setup?**  
   CLI, pre-commit hook, GitHub Action, IDE plugin, shared prompt file — choose by actual fit.

5. **Are the rules readable?**  
   Transparent rules are adjustable. A black-box API wrapper is a dependency you can neither tune nor audit.

6. **Is it built for your domain?**  
   Chinese prose, English blog, UI, and PR slop are different problems. A tool built for one domain rarely transfers to another.

## Suggested Workflow

### For writing

1. Draft first.
2. Run anti-slop rules on structure, phrasing, rhythm.
3. Add what only the author knows: specific numbers, real examples, edge cases, opinions.
4. Humanizer for local polish only.
5. Fact-check before publishing.

### For frontend

1. Define the product's personality and information hierarchy before generating any UI.
2. Use [taste-skill](https://github.com/Leonxlnx/taste-skill) or [impeccable](https://github.com/pbakaus/impeccable) to set hard constraints on layout, type, motion, and spacing.
3. Audit the output: remove template heroes, cheap gradients, filler cards, redundant CTAs.
4. Test with real content and real edge-state data.

### For code and PRs

1. Define edge cases, test expectations, and acceptance criteria before AI generates the code.
2. Set up a linter or GitHub Action to block bulk AI-generated PRs.
3. Every PR must explain intent, risk, and test approach. "Refactor" is not an explanation.
4. Review diffs for reordering, comment inflation, and meaningless abstraction layers.
5. Record failure patterns in the team agent rules.

## Contributing

Submit a PR. Each entry needs:

```markdown
- [owner/repo](https://github.com/owner/repo) - One-sentence description of what it does.
  - Type: Skill / Prompt / CLI / App / GitHub Action / Linter / Directory
  - Best for: Chinese writing / English docs / Academic / Frontend / PR / Code quality / Design
  - Why it matters: What AI slop problem does it solve?
  - Caveat: Does it promote detector bypass? Is it inactive? Does it depend on a closed-source API?
```

Leave out:

- Anything whose main pitch is "100% undetectable";
- No source, no rules, no docs;
- Fork with nothing new;
- Pure closed-source SaaS;
- Tools designed to help people cheat.

## License

MIT
