# Criterion-Level Verification

Verify the current research report and supporting artifacts against every executable
rubric criterion. Diagnose omissions; do not revise the artifact in this stage.

## Inputs

- `.autoscirub/executable_rubric.json`
- current report and user-specified deliverables
- supporting code, results, tables, figures, logs, and analysis files
- optional previous verification report

## Procedure

1. Check every criterion independently before judging overall status.
2. Require both the requested analysis and its supporting task-generated evidence.
3. Treat literature-only statements as insufficient when a criterion requires new evidence.
4. Verify that conclusions follow from artifacts rather than assertion.
5. Check expected filenames, captions, report references, and interpretable descriptions.
6. Name each missing experiment, comparison, metric, artifact, or explanation precisely.
7. Preserve criterion IDs across rounds.

Mark `all_satisfied` true only when all required and high-priority criteria pass and
any remaining medium or low criteria are explicitly justified by the rubric or user scope.

## Output

Write `.autoscirub/verification_report.json`, or a round-specific verification file:

```json
{
  "schema_version": "1.0",
  "round": 0,
  "all_satisfied": false,
  "criteria": [
    {
      "criterion_id": "C1",
      "satisfied": false,
      "evidence_found": ["report section or relative path"],
      "evidence_gap": "Specific missing evidence.",
      "required_actions": ["Concrete corrective action"],
      "artifact_references": ["relative/path or report anchor"]
    }
  ],
  "summary": {
    "passed": 0,
    "failed": 1,
    "highest_priority_gaps": ["..."]
  }
}
```
