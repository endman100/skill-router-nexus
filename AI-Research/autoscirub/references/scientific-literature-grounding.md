# Scientific Literature Grounding

Map each rubric goal to established scientific practice. Produce execution-driving
guidance, not a narrative literature review.

## Inputs

- `.autoscirub/rubric_skeleton.json`
- task instruction and optional `.autoscirub/config.yaml`
- task-visible literature and public first-party or scholarly sources
- any user or harness exclusions

## Procedure

1. Search broad concepts, method families, metrics, protocols, datasets, and benchmarks.
2. Prefer papers, preprints, official dataset or benchmark pages, method repositories,
   and authoritative software documentation.
3. Apply exclusions and hidden-target blocklists before reading full text.
4. Keep 5–7 strong core sources when enough relevant sources exist.
5. Organize findings by goal rather than by paper.
6. Record methods, metrics, baselines, controls, robustness checks, evidence forms, and
   questions that must be resolved during data exploration.
7. Mark uncertain or conflicting guidance explicitly.

Use the active agent's search tools. If a separate search skill is required, return to
the Router for a dependency expansion. Literature claims may guide experiment design,
but do not count as evidence produced for the current task.

## Output

Write `.autoscirub/literature_grounding.json`:

```json
{
  "schema_version": "1.0",
  "sources": [
    {
      "source_id": "S1",
      "title": "...",
      "url_or_path": "...",
      "source_type": "paper | preprint | documentation | dataset | benchmark | repository | other",
      "used_for_goal_ids": ["G1"]
    }
  ],
  "goals": [
    {
      "goal_id": "G1",
      "queries": ["..."],
      "source_ids": ["S1"],
      "methods": ["method and relevance"],
      "metrics": ["metric and interpretation"],
      "baselines": ["..."],
      "controls": ["..."],
      "robustness_checks": ["..."],
      "evidence_forms": ["artifact and what it must show"],
      "feasibility_questions": ["..."]
    }
  ]
}
```
