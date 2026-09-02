# Criterion Synthesis

Combine instruction-derived goals, literature grounding, and data feasibility into
a compact executable rubric. This rubric becomes the contract for execution,
verification, and revision.

## Inputs

- `.autoscirub/rubric_skeleton.json`
- `.autoscirub/literature_grounding.json`
- `.autoscirub/task_data_profile.json`
- optional task configuration or profile

## Procedure

1. Preserve every skeleton goal unless visible data proves it infeasible.
2. Select feasible analyses that best satisfy each goal.
3. Convert requirements into observable criteria with stable IDs.
4. Link every criterion to goals, data, required analyses, comparisons, artifacts,
   satisfaction conditions, priorities, and provenance.
5. Record unsupported or risky claim patterns the execution agent must avoid.
6. Prefer 6–15 criteria; remove redundancy instead of rewarding length.

Reject generic criteria such as "analyze thoroughly". Do not require unavailable
labels, tools, target answers, private data, or unsupported surrogate analyses.

## Output

Write `.autoscirub/executable_rubric.json`:

```json
{
  "schema_version": "1.0",
  "goals": [{"goal_id": "G1", "title": "...", "requirement": "..."}],
  "criteria": [
    {
      "criterion_id": "C1",
      "goal_ids": ["G1"],
      "requirement": "Concrete requirement.",
      "data_sources": ["relative/path or field"],
      "required_analysis": ["experiment or diagnostic"],
      "metrics": ["metric or qualitative check"],
      "comparisons": ["baseline or control"],
      "expected_artifacts": [
        {
          "type": "figure | table | number | file | code | text_analysis",
          "name": "semantic artifact name",
          "expected_path": "optional/relative/path",
          "must_show": "observable evidence"
        }
      ],
      "satisfaction_condition": "Observable pass condition.",
      "priority": "high | medium | low",
      "provenance": {
        "instruction": ["..."],
        "literature": ["S1"],
        "data_profile": ["..."]
      }
    }
  ],
  "claims_to_avoid": ["..."]
}
```
