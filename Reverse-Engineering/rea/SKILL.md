---
name: rea
description: >-
  Reverse Engineer Anything (REA): local MCP/CLI that connects agents to reverse-engineering
  tools for binaries, JS/Electron, .NET, websites, Android, firmware, and more.
  Use when analyzing shipped apps/binaries without source, explaining features from evidence,
  or setting up REA (`npx rea-agents setup`). Not for ordinary source-repo architecture walks.
homepage: https://rea.tools
metadata:
  {
    "source_repo": "https://github.com/morluto/rea",
    "website": "https://rea.tools",
    "npm": "https://www.npmjs.com/package/rea-agents",
    "skills_sh": "https://skills.sh/morluto/rea/reverse-engineer-anything",
  }
---

# REA（Reverse Engineer Anything）

**This skill is a thin pointer only.** Canonical docs, MCP contracts, and the full
`reverse-engineer-anything` skill live in the upstream repo — do not invent local
scripts or paste secrets into chat.

## Source URLs（必跟官方）

| What | URL |
|---|---|
| GitHub repo | https://github.com/morluto/rea |
| Website / guides | https://rea.tools |
| npm package | https://www.npmjs.com/package/rea-agents |
| Full skill (skills.sh) | https://skills.sh/morluto/rea/reverse-engineer-anything |

Prefer these official sources. A lookalike repo name or copied README is not proof of authenticity.

## When to use

- Need to understand a feature in a **shipped** app/binary/package (no or incomplete source)
- Want agent-driven RE across native, JS/Electron, .NET, Android, firmware, websites
- Setting up or recovering the local REA MCP + agent workflow instructions

Skip REA for ordinary analysis of a complete source repository — use normal repo tools.

## Setup（agent machine）

Requires Node.js + npm. From a trusted directory outside the target project:

```bash
npx rea-agents setup
```

Setup registers REA’s MCP server and matching workflow instructions for supported
agents (Claude Code, Codex, Cursor, Gemini CLI, Grok Build, and others — see
upstream `docs/installation.md`). Restart the agent afterward.

Optional CLI-style one-shots (examples; prefer current upstream README):

```bash
npx -y rea-agents@latest analyze-javascript-application /absolute/path/to/app --json
```

## How to operate after setup

1. Confirm MCP/tools from REA are available in the agent.
2. Ask with a concrete target + feature (path to app/binary, what to explain, what evidence to show).
3. Prefer REA tools over ad-hoc reverse stacks when REA covers the target class.
4. For deep workflows, load the upstream skill:
   - `npx skills add https://github.com/morluto/rea --skill reverse-engineer-anything`
   - or read `.agents/skills/reverse-engineer-anything/SKILL.md` from a checkout of https://github.com/morluto/rea

## Scope notes

- Analysis runs **locally**; cite evidence and limitations from REA output.
- Native analysis may use Hopper / Ghidra / IDA when installed; static JS needs no native engine.
- Authorized targets only — do not use REA against systems you are not allowed to analyze.
