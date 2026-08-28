---
name: lycheememory-agent-memory
description: Apply or evaluate LycheeMemory's long-term memory method for LLM agents, including bounded working memory, typed semantic records, online consolidation and conflict-aware fusion, hierarchical retrieval, procedural skill memory, and action or usage feedback. Use when designing agent memory, comparing memory architectures, planning persistent recall, or when the user mentions LycheeMem or LycheeMemory.
---

# LycheeMemory Agent Memory

**Scale ID / Skill ID:** `lycheememory-agent-memory`

**Official source:** <https://github.com/LycheeMem/LycheeMem>

Treat the official repository as the source of truth. This Skill is an external-reference wrapper and does not vendor, reproduce, or install LycheeMemory code.

## Method

1. Keep recent conversation turns in a token-bounded working-memory window and consolidate older context at pressure or session boundaries.
2. Convert durable information into self-contained, typed semantic records such as facts, preferences, events, constraints, procedures, failure patterns, and tool affordances.
3. Deduplicate and fuse related records online, preserve conflicts and provenance, and organize the results into a hierarchy rather than a flat summary list.
4. Retrieve hierarchically: use the query, recent context, intended action, constraints, and missing information to select broad composite memories, then expand to atomic evidence when necessary.
5. Keep reusable procedures in a separate skill store whose intent supports semantic retrieval of the full procedure.
6. Record retrieval usage and downstream outcomes so future recall and ranking can become usage-aware.

## Apply the Reference

- Open the official repository before recommending installation, configuration, APIs, integrations, thresholds, or current capabilities.
- Distinguish working, semantic, procedural, and visual memory instead of treating all stored context as one vector index.
- Preserve stable session and user boundaries when adapting the method to another agent runtime.
- Cite the official repository when presenting this method, and label any adaptation or simplification as such.
- Do not claim that LycheeMemory is installed or available locally unless the environment has been checked.
