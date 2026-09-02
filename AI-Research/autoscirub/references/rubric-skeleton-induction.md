# Rubric Skeleton Induction

Transform an underspecified research instruction into a compact set of atomic
scientific goals. Define what the task must address without deciding how to prove it.

## Inputs

Use only the user's research instruction or an explicitly named instruction file.
Do not read literature, web sources, data schemas, prior outputs, report drafts,
hidden benchmark files, target papers, or detailed code during this stage.

## Procedure

1. Extract the main scientific objectives, comparisons, analyses, and interpretation needs.
2. Split compound requirements only when separate evidence will be required.
3. Assign stable goal identifiers `G1`, `G2`, and so on in task-logical order.
4. Record the instruction phrase or faithful paraphrase supporting each goal.
5. Prefer 3–7 literal, non-overlapping goals. Record a conservative interpretation
   instead of silently expanding ambiguous scope.

Do not add methods, metrics, baselines, tests, plots, expected results, or claims that
are absent from the instruction.

## Output

Write `.autoscirub/rubric_skeleton.json`:

```json
{
  "schema_version": "1.0",
  "task_id": "optional-stable-id",
  "source": "instruction",
  "goals": [
    {
      "goal_id": "G1",
      "title": "Short goal title",
      "requirement": "Concrete scientific requirement implied by the instruction.",
      "instruction_evidence": ["Quote or faithful paraphrase"]
    }
  ]
}
```
