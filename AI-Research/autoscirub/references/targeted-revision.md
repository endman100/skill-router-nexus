# Targeted Revision

Perform exactly one bounded revision round using failed rubric criteria and the latest
criterion-level verification report.

## Inputs

- `.autoscirub/executable_rubric.json`
- latest verification report
- current report and supporting artifacts
- visible data, code, and tools needed to address the gaps

## Procedure

1. Select failed criteria, prioritizing required and high-priority evidence gaps.
2. Convert each gap into concrete work: run a missing analysis, add a comparison,
   regenerate an artifact, strengthen an explanation, or remove an unsupported claim.
3. Record a revision plan before substantive changes when practical.
4. Change only the code, results, figures, tables, and report text needed for those gaps.
5. Preserve supported results unless new evidence contradicts them.
6. Record completed actions, changed artifacts, and remaining gaps.
7. Return control to criterion-level verification. Never declare the revision successful
   solely because files changed.

Do not broaden scope beyond failed criteria except for a necessary dependency. If a fix
is infeasible, document why and revise the report so it does not make an unsupported claim.

## Outputs

For revision round `N`, write:

```text
.autoscirub/revisions/round-NNN/revision_plan.json
.autoscirub/revisions/round-NNN/change_summary.json
```

Each target in `revision_plan.json` must name its `criterion_id`, evidence gap, planned
actions, expected artifacts, and risks. Each entry in `change_summary.json` must name
actions completed, artifacts changed, and the remaining gap or `none`.
