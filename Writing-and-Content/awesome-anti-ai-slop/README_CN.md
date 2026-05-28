# Awesome Anti AI Slop

> 去除 AI 味工具合集。

[![Awesome](https://awesome.re/badge.svg)](https://awesome.re)
![Last Updated](https://img.shields.io/badge/updated-2026--05--27-blue)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

[English README](./README.md)

## What is AI slop?

**AI slop** 是 AI 生成或辅助生成的内容中可识别的低质量痕迹：

- 空洞、模板化、过度平滑的文字；
- "不仅……而且……""总之""值得注意的是"等机械连接词；
- 大量正确但没洞察的泛泛而谈；
- 代码里看似完整但缺少边界条件、测试、异常处理；
- PR 里批量生成的低质量改动；
- UI 里千篇一律的卡片、渐变、居中 hero、无意义动效；
- 设计语言、排版、间距、信息层级缺乏判断力。

宣传"绝对过检"的项目不在收录范围内。

## Selection Criteria

收录标准：

1. **开源且可直接使用**：skill、prompt、CLI、app、GitHub Action、linter、规则集。
2. **对质量有实质改善**：文字、代码、PR、UI 或设计，非同义词替换 API 的简单封装。
3. **有可验证的价值**：star 数、fork 数、真实使用场景、实现质量，至少具备其一。
4. **非营销空壳**：无源码、无规则集、以绕过检测为卖点的项目不予收录。
5. **可集成至常见工作流**：Claude Code、Codex、Cursor、CI、pre-commit 或团队文档。

> Star 数据为整理时的快照，随时间变化。

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
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | [![Stars](https://img.shields.io/github/stars/pbakaus/impeccable?style=social)](https://github.com/pbakaus/impeccable) | Frontend / UI / design anti-slop | 针对 AI 生成网页的常见问题：渐变背景、居中 hero、无差别卡片排布。本方向关注度最高的项目。 |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | [![Stars](https://img.shields.io/github/stars/Leonxlnx/taste-skill?style=social)](https://github.com/Leonxlnx/taste-skill) | AI-built frontend taste | 为 AI 生成的前端页面设定 layout、字体、动效、间距约束的 skill 框架，支持 Codex、Cursor、Claude Code。 |
| [blader/humanizer](https://github.com/blader/humanizer) | [![Stars](https://img.shields.io/github/stars/blader/humanizer?style=social)](https://github.com/blader/humanizer) | English writing humanizer | 英文写作去 AI 味，适用于文章、文档、邮件及文案。 |
| [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | [![Stars](https://img.shields.io/github/stars/Imbad0202/academic-research-skills?style=social)](https://github.com/Imbad0202/academic-research-skills) | Research / academic workflow | 学术研究质量、论文结构与写法校准的综合工具集，范围超出单纯的文本润色。 |
| [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) | [![Stars](https://img.shields.io/github/stars/op7418/Humanizer-zh?style=social)](https://github.com/op7418/Humanizer-zh) | 中文写作 | 中文去 AI 味，适用于文章、学术初稿、公众号及商业文案。 |
| [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | [![Stars](https://img.shields.io/github/stars/hardikpandya/stop-slop?style=social)](https://github.com/hardikpandya/stop-slop) | Prompt rules / prose cleanup | 基于规则，可作为自定义 system prompt 或 Claude Project 指令文件的起点。 |
| [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | [![Stars](https://img.shields.io/github/stars/conorbronsdon/avoid-ai-writing?style=social)](https://github.com/conorbronsdon/avoid-ai-writing) | Detect + rewrite workflow | 分检测与重写两种模式，适用于内容团队的草稿审查流程。 |
| [peakoss/anti-slop](https://github.com/peakoss/anti-slop) | [![Stars](https://img.shields.io/github/stars/peakoss/anti-slop?style=social)](https://github.com/peakoss/anti-slop) | GitHub PR quality gate | GitHub Action，在低质量 AI slop PR 合并前拦截。 |
| [mshumer/unslop](https://github.com/mshumer/unslop) | [![Stars](https://img.shields.io/github/stars/mshumer/unslop?style=social)](https://github.com/mshumer/unslop) | Custom anti-slop instructions | 分析写作样本或品牌样本，提取模型的默认套路，生成可复用指令文件。 |
| [brandonwise/humanizer](https://github.com/brandonwise/humanizer) | [![Stars](https://img.shields.io/github/stars/brandonwise/humanizer?style=social)](https://github.com/brandonwise/humanizer) | CLI / local audit | 关注度较低，但本地工作流完整：评分、分析、diff、建议，无需云端 API。 |

## Starter Stacks

### 中文写作

- [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) — 主力中文去 AI 味。
- [cangtianhuang/humanizer-academic-zh](https://github.com/cangtianhuang/humanizer-academic-zh) — 中文学术写作专用。
- [marswjf/stop-slop-zh](https://github.com/marswjf/stop-slop-zh) — 中英双语规则型 de-slop skill。
- [1-SKILL/shuorenhua](https://github.com/1-SKILL/shuorenhua) — 中文"说人话"方向的小型项目。

### 英文博客 / 文档 / 产品文案

- [blader/humanizer](https://github.com/blader/humanizer) — 主力 humanizer。
- [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) — 规则底稿。
- [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) — detect + rewrite。
- [jalaalrd/anti-ai-slop-writing](https://github.com/jalaalrd/anti-ai-slop-writing) — 轻量 anti-slop writing prompt。

### 前端 / UI / 产品设计

- [pbakaus/impeccable](https://github.com/pbakaus/impeccable) — 前端/UI anti-slop。
- [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) — AI-built frontend taste framework。
- [mshumer/unslop](https://github.com/mshumer/unslop) — 生成团队专属反 slop 指令。
- [Wholiver/swiftui-design-skill](https://github.com/Wholiver/swiftui-design-skill) — SwiftUI 设计方向。
- [Hacksore/oghunt](https://github.com/Hacksore/oghunt) — Product Hunt 信息流去 AI 噪声。

### 代码 / PR / 团队治理

- [peakoss/anti-slop](https://github.com/peakoss/anti-slop) — GitHub Action。
- [scanaislop/aislop](https://github.com/scanaislop/aislop) — AI code quality gate / hook / MCP。
- [JordanGunn/agent-slop-lint](https://github.com/JordanGunn/agent-slop-lint) — agentic coding linter。
- [yuvrajangadsingh/vibecheck](https://github.com/yuvrajangadsingh/vibecheck) — JS/TS/Python slop lint。
- [HugoLopes45/llmstrip](https://github.com/HugoLopes45/llmstrip) — 轻量清理 prose / comments / commits。

## Text & Writing

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [blader/humanizer](https://github.com/blader/humanizer) | [![Stars](https://img.shields.io/github/stars/blader/humanizer?style=social)](https://github.com/blader/humanizer) | Skill | 英文写作去 AI 味，适用于文档、博客及邮件。 |
| [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | [![Stars](https://img.shields.io/github/stars/hardikpandya/stop-slop?style=social)](https://github.com/hardikpandya/stop-slop) | Skill / rules | 识别 banned phrases、结构套路、句子级 AI 痕迹。 |
| [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | [![Stars](https://img.shields.io/github/stars/conorbronsdon/avoid-ai-writing?style=social)](https://github.com/conorbronsdon/avoid-ai-writing) | Skill / workflow | 分检测与重写两种模式，内容团队使用。 |
| [jalaalrd/anti-ai-slop-writing](https://github.com/jalaalrd/anti-ai-slop-writing) | [![Stars](https://img.shields.io/github/stars/jalaalrd/anti-ai-slop-writing?style=social)](https://github.com/jalaalrd/anti-ai-slop-writing) | Prompt | 针对词汇、结构、标点、格式的轻量规则包。 |
| [coderjatin/anti-slop-writing](https://github.com/coderjatin/anti-slop-writing) | [![Stars](https://img.shields.io/github/stars/coderjatin/anti-slop-writing?style=social)](https://github.com/coderjatin/anti-slop-writing) | Prompt | 可用于 Claude Code、Gemini CLI、Codex CLI、Copilot、Cursor 等。 |
| [stephenturner/skill-deslop](https://github.com/stephenturner/skill-deslop) | [![Stars](https://img.shields.io/github/stars/stephenturner/skill-deslop?style=social)](https://github.com/stephenturner/skill-deslop) | Skill | 科学/技术写作 de-slop，针对公式化结构、filler、false agency。 |
| [rankgnar/deslop](https://github.com/rankgnar/deslop) | [![Stars](https://img.shields.io/github/stars/rankgnar/deslop?style=social)](https://github.com/rankgnar/deslop) | CLI | 检测/移除 buzzwords、false profundity、空洞转折。 |
| [AUAggy/deslop](https://github.com/AUAggy/deslop) | [![Stars](https://img.shields.io/github/stars/AUAggy/deslop?style=social)](https://github.com/AUAggy/deslop) | VS Code / rewrite | 选择文本后按严格规则重写，不生成新内容。 |
| [gabelul/slopbuster](https://github.com/gabelul/slopbuster) | [![Stars](https://img.shields.io/github/stars/gabelul/slopbuster?style=social)](https://github.com/gabelul/slopbuster) | Audit / rules | prose、code、academic writing 审查，包含多模式 audit 思路。 |
| [ksanyok/TextHumanize](https://github.com/ksanyok/TextHumanize) | [![Stars](https://img.shields.io/github/stars/ksanyok/TextHumanize?style=social)](https://github.com/ksanyok/TextHumanize) | Library | 离线算法库，多语言文本归一化，与检测器绕过无关。 |
| [HugoLopes45/llmstrip](https://github.com/HugoLopes45/llmstrip) | [![Stars](https://img.shields.io/github/stars/HugoLopes45/llmstrip?style=social)](https://github.com/HugoLopes45/llmstrip) | Rust CLI | 清理 prose、代码注释、commit 信息里的 LLM 痕迹。 |
| [avectats7/anti-ai-writing](https://github.com/avectats7/anti-ai-writing) | [![Stars](https://img.shields.io/github/stars/avectats7/anti-ai-writing?style=social)](https://github.com/avectats7/anti-ai-writing) | Prompt | 英语/西语规则包，针对 banned words、phrases、structures。 |

## Chinese Writing

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) | [![Stars](https://img.shields.io/github/stars/op7418/Humanizer-zh?style=social)](https://github.com/op7418/Humanizer-zh) | Skill | 中文去 AI 味，适用于稿件、商业文案及论文初稿。 |
| [cangtianhuang/humanizer-academic-zh](https://github.com/cangtianhuang/humanizer-academic-zh) | [![Stars](https://img.shields.io/github/stars/cangtianhuang/humanizer-academic-zh?style=social)](https://github.com/cangtianhuang/humanizer-academic-zh) | Prompt / skill | 中文学术写作去 AI 痕迹。 |
| [marswjf/stop-slop-zh](https://github.com/marswjf/stop-slop-zh) | [![Stars](https://img.shields.io/github/stars/marswjf/stop-slop-zh?style=social)](https://github.com/marswjf/stop-slop-zh) | Skill / prompt | 中英双语 de-slop skill，支持 Claude Code、OpenClaw、Codex CLI、Cursor/Windsurf 等。 |
| [shyuan/writing-humanizer](https://github.com/shyuan/writing-humanizer) | [![Stars](https://img.shields.io/github/stars/shyuan/writing-humanizer?style=social)](https://github.com/shyuan/writing-humanizer) | Plugin / skill | 台湾繁中写作 humanizer。 |
| [1-SKILL/shuorenhua](https://github.com/1-SKILL/shuorenhua) | [![Stars](https://img.shields.io/github/stars/1-SKILL/shuorenhua?style=social)](https://github.com/1-SKILL/shuorenhua) | Skill | 中文"说人话"改写，小众但方向明确。 |

## Academic Writing

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | [![Stars](https://img.shields.io/github/stars/Imbad0202/academic-research-skills?style=social)](https://github.com/Imbad0202/academic-research-skills) | Skill collection | 学术研究全流程工具集：研究质量、论文写法与风格校准。 |
| [cangtianhuang/humanizer-academic-zh](https://github.com/cangtianhuang/humanizer-academic-zh) | [![Stars](https://img.shields.io/github/stars/cangtianhuang/humanizer-academic-zh?style=social)](https://github.com/cangtianhuang/humanizer-academic-zh) | Chinese academic | 中文学术写作专用 anti-AI-trace prompt/skill。 |
| [stephenturner/skill-deslop](https://github.com/stephenturner/skill-deslop) | [![Stars](https://img.shields.io/github/stars/stephenturner/skill-deslop?style=social)](https://github.com/stephenturner/skill-deslop) | Scientific / technical | 科学写作、技术博客、研究沟通中的 de-slop。 |
| [gabelul/slopbuster](https://github.com/gabelul/slopbuster) | [![Stars](https://img.shields.io/github/stars/gabelul/slopbuster?style=social)](https://github.com/gabelul/slopbuster) | Audit | prose/code/academic writing 审查与评分思路。 |

## Frontend, UI & Design Taste

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | [![Stars](https://img.shields.io/github/stars/pbakaus/impeccable?style=social)](https://github.com/pbakaus/impeccable) | Frontend / UI skill | 前端/UI/design anti-slop，专门处理 AI 生成网页的模板化问题。 |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | [![Stars](https://img.shields.io/github/stars/Leonxlnx/taste-skill?style=social)](https://github.com/Leonxlnx/taste-skill) | Frontend skill framework | Gives your AI good taste. 涵盖 layout、typography、motion、spacing、design-system、redesign audit 与 image-to-code 的约束规则。 |
| [mshumer/unslop](https://github.com/mshumer/unslop) | [![Stars](https://img.shields.io/github/stars/mshumer/unslop?style=social)](https://github.com/mshumer/unslop) | Instruction generator | 从文本或视觉样本中提取模型默认套路，生成可复用 instruction file。 |
| [Wholiver/swiftui-design-skill](https://github.com/Wholiver/swiftui-design-skill) | [![Stars](https://img.shields.io/github/stars/Wholiver/swiftui-design-skill?style=social)](https://github.com/Wholiver/swiftui-design-skill) | SwiftUI design skill | SwiftUI 设计方向，针对移动端 UI 质量。 |
| [Hacksore/oghunt](https://github.com/Hacksore/oghunt) | [![Stars](https://img.shields.io/github/stars/Hacksore/oghunt?style=social)](https://github.com/Hacksore/oghunt) | Product Hunt filter | 从 Product Hunt 信息流中移除 AI listing，偏信息噪声治理。 |

### Taste Skill install example

```bash
npx skills add https://github.com/Leonxlnx/taste-skill
npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"
```

界面有 AI 生成感时使用，文字去 AI 味问题请选其他工具。

## Code, PR & Engineering Slop

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [peakoss/anti-slop](https://github.com/peakoss/anti-slop) | [![Stars](https://img.shields.io/github/stars/peakoss/anti-slop?style=social)](https://github.com/peakoss/anti-slop) | GitHub Action | 检测并关闭低质量或 AI slop PR。 |
| [JordanGunn/agent-slop-lint](https://github.com/JordanGunn/agent-slop-lint) | [![Stars](https://img.shields.io/github/stars/JordanGunn/agent-slop-lint?style=social)](https://github.com/JordanGunn/agent-slop-lint) | Linter | 面向 agentic coding 的语言无关代码质量 linter。 |
| [scanaislop/aislop](https://github.com/scanaislop/aislop) | [![Stars](https://img.shields.io/github/stars/scanaislop/aislop?style=social)](https://github.com/scanaislop/aislop) | Hook / MCP / quality gate | 面向 Claude Code、Cursor、Codex 的 AI 代码质量门禁。 |
| [yuvrajangadsingh/vibecheck](https://github.com/yuvrajangadsingh/vibecheck) | [![Stars](https://img.shields.io/github/stars/yuvrajangadsingh/vibecheck?style=social)](https://github.com/yuvrajangadsingh/vibecheck) | JS/TS/Python linter | 类似 ESLint 的 AI slop 检测。 |
| [adamcharnock/deslop](https://github.com/adamcharnock/deslop) | [![Stars](https://img.shields.io/github/stars/adamcharnock/deslop?style=social)](https://github.com/adamcharnock/deslop) | pre-commit prose lint | 提交前检查文档和 prose 里的 AI 写作模式。 |
| [HugoLopes45/llmstrip](https://github.com/HugoLopes45/llmstrip) | [![Stars](https://img.shields.io/github/stars/HugoLopes45/llmstrip?style=social)](https://github.com/HugoLopes45/llmstrip) | CLI | 清理代码注释、commit message、prose 里的 LLM 痕迹。 |

## Apps, CLIs & Workbenches

| Project | Stars | Type | Notes |
|---|---:|---|---|
| [lynote-ai/humanize-text](https://github.com/lynote-ai/humanize-text) | [![Stars](https://img.shields.io/github/stars/lynote-ai/humanize-text?style=social)](https://github.com/lynote-ai/humanize-text) | App | App 型文本 humanizer，关注度较高，适合作为编辑辅助工具，非检测绕过工具。 |
| [DadaNanjesha/AI-Text-Humanizer-App](https://github.com/DadaNanjesha/AI-Text-Humanizer-App) | [![Stars](https://img.shields.io/github/stars/DadaNanjesha/AI-Text-Humanizer-App?style=social)](https://github.com/DadaNanjesha/AI-Text-Humanizer-App) | App | 正式、学术风格改写 App。 |
| [brandonwise/humanizer](https://github.com/brandonwise/humanizer) | [![Stars](https://img.shields.io/github/stars/brandonwise/humanizer?style=social)](https://github.com/brandonwise/humanizer) | CLI / OpenClaw skill | 本地工作流：评分、分析、报告、建议、扫描、diff，无需云端 API。 |
| [rudra496/StealthHumanizer](https://github.com/rudra496/StealthHumanizer) | [![Stars](https://img.shields.io/github/stars/rudra496/StealthHumanizer?style=social)](https://github.com/rudra496/StealthHumanizer) | App / multi-provider | 多 provider、多重写等级，"stealth/bypass"导向明显，慎用。 |
| [ZAYUVALYA/AI-Text-Humanizer](https://github.com/ZAYUVALYA/AI-Text-Humanizer) | [![Stars](https://img.shields.io/github/stars/ZAYUVALYA/AI-Text-Humanizer?style=social)](https://github.com/ZAYUVALYA/AI-Text-Humanizer) | App / paraphrasing | 上下文感知 paraphrasing，早期阶段。 |
| [dixon2004/ai-humanizer](https://github.com/dixon2004/ai-humanizer) | [![Stars](https://img.shields.io/github/stars/dixon2004/ai-humanizer?style=social)](https://github.com/dixon2004/ai-humanizer) | Web/local app | Gemini 驱动的小型 humanizer。 |
| [puneethkotha/humanizer-workbench](https://github.com/puneethkotha/humanizer-workbench) | [![Stars](https://img.shields.io/github/stars/puneethkotha/humanizer-workbench?style=social)](https://github.com/puneethkotha/humanizer-workbench) | CLI / skill | humanizer workbench，小众项目。 |
| [itsjwill/humanizer-x](https://github.com/itsjwill/humanizer-x) | [![Stars](https://img.shields.io/github/stars/itsjwill/humanizer-x?style=social)](https://github.com/itsjwill/humanizer-x) | Agent / workflow | 4-pass humanizer + voice agent，小众项目。 |

## Directories & Meta Lists

| Project / Topic | Stars | Notes |
|---|---:|---|
| [shannhk/avoid-slop](https://github.com/shannhk/avoid-slop) | [![Stars](https://img.shields.io/github/stars/shannhk/avoid-slop?style=social)](https://github.com/shannhk/avoid-slop) | 专门收集 text、code、design 反 AI slop 工具。 |
| [GitHub Topic: ai-humanizer](https://github.com/topics/ai-humanizer) | - | 文本 humanizer app / skill / prompt 集合。 |
| [GitHub Topic: humanize-text](https://github.com/topics/humanize-text) | - | 更窄的文本 humanizer topic。 |
| [GitHub Topic: ai-slop](https://github.com/topics/ai-slop) | - | 覆盖 PR、代码、UI、设计、内容噪声等更广义 AI slop。 |

## Niche / Experimental

关注度低或场景较窄，部分含"绕过检测"话术。规则与实现可供参考，输出不建议直接依赖。

| Project | Stars | Notes |
|---|---:|---|
| [Aboudjem/humanizer-skill](https://github.com/Aboudjem/humanizer-skill) | [![Stars](https://img.shields.io/github/stars/Aboudjem/humanizer-skill?style=social)](https://github.com/Aboudjem/humanizer-skill) | Claude Code skill，包含多模式与 voice profile。 |
| [Firdavs-coder/ai_humanizer](https://github.com/Firdavs-coder/ai_humanizer) | [![Stars](https://img.shields.io/github/stars/Firdavs-coder/ai_humanizer?style=social)](https://github.com/Firdavs-coder/ai_humanizer) | 更偏 prompt/model release。 |
| [Hakku/finnish-humanizer](https://github.com/Hakku/finnish-humanizer) | [![Stars](https://img.shields.io/github/stars/Hakku/finnish-humanizer?style=social)](https://github.com/Hakku/finnish-humanizer) | 芬兰语 humanizer。 |
| [lguz/humanize-writing-skill](https://github.com/lguz/humanize-writing-skill) | [![Stars](https://img.shields.io/github/stars/lguz/humanize-writing-skill?style=social)](https://github.com/lguz/humanize-writing-skill) | Claude skill，三段式编辑思路。 |
| [199-biotechnologies/humanise-text-skill](https://github.com/199-biotechnologies/humanise-text-skill) | [![Stars](https://img.shields.io/github/stars/199-biotechnologies/humanise-text-skill?style=social)](https://github.com/199-biotechnologies/humanise-text-skill) | Claude Code skill，规则清单型。 |
| [diaiq/claude-skill-humanizer](https://github.com/diaiq/claude-skill-humanizer) | [![Stars](https://img.shields.io/github/stars/diaiq/claude-skill-humanizer?style=social)](https://github.com/diaiq/claude-skill-humanizer) | Claude Code skill，注意甄别检测器绕过宣传。 |
| [imsv1301/unmask-ai](https://github.com/imsv1301/unmask-ai) | [![Stars](https://img.shields.io/github/stars/imsv1301/unmask-ai?style=social)](https://github.com/imsv1301/unmask-ai) | 检测 + humanize 包装。 |
| [ofershap/ai-humanizer](https://github.com/ofershap/ai-humanizer) | [![Stars](https://img.shields.io/github/stars/ofershap/ai-humanizer?style=social)](https://github.com/ofershap/ai-humanizer) | 低星项目，宣传偏 undetectable，慎用。 |
| [asazonov/deslop-codex](https://github.com/asazonov/deslop-codex) | [![Stars](https://img.shields.io/github/stars/asazonov/deslop-codex?style=social)](https://github.com/asazonov/deslop-codex) | Codex skill package，关注度较低。 |

## How to Evaluate an Anti-Slop Tool

选用工具前的核查项：

1. **同义词替换，还是结构性改写？**  
   低质量工具的常见手段：换词、插口语、加错别字。改善结构、节奏与信息密度的工具才有实质价值。

2. **是否声称可绕过检测器？**  
   AI 检测器误判率高且持续迭代，以"bypass Turnitin / GPTZero"为主要卖点的项目可信度存疑。

3. **是否改动原文事实？**  
   改写应保留原文的事实、立场与限制条件。凭空添加细节或弱化结论的工具不可用。

4. **是否可集成至现有工作流？**  
   CLI、pre-commit、GitHub Action、IDE 插件、共享 prompt 文件，按实际需要选择。

5. **规则是否透明可读？**  
   透明的规则集可由团队自行调整；黑盒 API 包装器既无法调整，也无法审计。

6. **是否针对具体使用场景？**  
   中文写作、英文博客、UI、PR 的 slop 类型各异，针对某一场景的工具通常无法直接迁移至其他场景。

## Suggested Workflow

### For writing

1. 完成初稿。
2. 用 anti-slop 规则检查结构、措辞与节奏。
3. 补充作者独有的内容：具体数据、真实案例、边界条件与个人判断。
4. Humanizer 仅用于局部润色。
5. 发布前做事实核查。

### For frontend

1. 明确产品气质与信息层级，再开始使用 AI 生成界面。
2. 用 [taste-skill](https://github.com/Leonxlnx/taste-skill) 或 [impeccable](https://github.com/pbakaus/impeccable) 对 layout、字体、动效、间距设硬约束。
3. 审查生成结果，移除模板化 hero、廉价渐变、占位卡片及冗余 CTA。
4. 以真实内容与边界状态测试。

### For code and PRs

1. 在 AI 生成代码前，明确边界条件、测试预期与验收标准。
2. 配置 linter 或 GitHub Action，拦截批量 AI 生成的 PR。
3. 每个 PR 须说明意图、风险与测试方式，仅写"Refactor"不予受理。
4. 重点审查 diff 中的重排序、注释膨胀与无实质意义的抽象层。
5. 将发现的失败模式记录至团队 agent rules。

## Contributing

提 PR 请带上：

```markdown
- [owner/repo](https://github.com/owner/repo) - 一句话说明用途。
  - Type: Skill / Prompt / CLI / App / GitHub Action / Linter / Directory
  - Best for: 中文写作 / 英文文档 / 学术 / 前端 / PR / 代码质量 / 设计
  - Why it matters: 它解决什么 AI slop 问题？
  - Caveat: 是否有检测器绕过宣传、是否维护不活跃、是否依赖闭源 API？
```

不收：

- 主要卖点是"100% undetectable"的；
- 没有源码、没有规则、没有文档的壳；
- fork 了但没加任何新东西的；
- 纯闭源 SaaS；
- 帮人作弊的工具。

## License

MIT
