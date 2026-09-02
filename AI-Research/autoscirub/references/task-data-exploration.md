# Task-Data Exploration

Build a lightweight profile of task-visible data, code, tools, and constraints. Use
the profile to decide which literature-grounded analyses are actually feasible.

## Inputs

- `.autoscirub/rubric_skeleton.json`
- `.autoscirub/literature_grounding.json`
- task instruction and optional configuration
- visible project files, datasets, code, metadata, and tool documentation

## Procedure

1. List relevant files, formats, sizes, and likely roles.
2. Inspect schemas, dimensions, fields, units, labels, timestamps, conditions, and IDs.
3. Sample small previews when safe.
4. Identify joins, alignment keys, cross-source relationships, and missing values.
5. Identify available utilities and their command interfaces.
6. Record dependency and compute risks without selecting a machine-specific environment.
7. Map each goal to supporting files, feasible analyses, and unsupported requirements.

Do not run full training, expensive simulations, final figure generation, or report
writing. Do not invent labels, ground truth, units, coordinates, or reference values.

## Output

Write `.autoscirub/task_data_profile.json`:

```json
{
  "schema_version": "1.0",
  "files": [
    {
      "path": "relative/path",
      "format": "csv | json | hdf5 | image | text | code | other",
      "size_or_shape": "...",
      "key_fields": ["..."],
      "role": "input | label | reference | metadata | geometry | time_series | model_output | code | other",
      "notes": "..."
    }
  ],
  "datasets": [],
  "relationships": [],
  "constraints": [],
  "goal_support": [
    {
      "goal_id": "G1",
      "supporting_files": ["..."],
      "feasible_analyses": ["..."],
      "unsupported_requirements": ["..."],
      "notes": "..."
    }
  ],
  "dependency_notes": []
}
```
