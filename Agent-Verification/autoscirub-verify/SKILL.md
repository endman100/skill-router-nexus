---
name: autoscirub-verify
description: Verify a scientific report and its code, results, tables, and figures criterion by criterion against an existing `.autoscirub/executable_rubric.json`, then produce concrete evidence gaps and optionally hand failed criteria to one bounded targeted revision round. Use only when an AutoSciRub rubric already exists or the user explicitly requests AutoSciRub verification. This scientific artifact check supplements rather than replaces general completion verification.
---

# AutoSciRub Verify

Use this verification-only entry when rubric induction is already complete. If no
`.autoscirub/executable_rubric.json` exists, stop and route to the full `autoscirub`
workflow in `AI-Research` instead of inventing criteria after execution.

## Verify

1. Read the executable rubric, current report, and supporting code, results, tables,
   figures, logs, and analysis files.
2. Check each criterion independently and preserve its stable identifier.
3. Mark a criterion satisfied only when both the requested analysis and inspectable
   task-generated evidence exist.
4. Do not substitute literature claims for current-task evidence.
5. Record evidence found, the exact gap, required corrective actions, and artifact paths.
6. Write `.autoscirub/verification_report.json` or the requested round-specific file.
7. Set `all_satisfied` true only when all required and high-priority criteria pass and
   lower-priority exceptions are explicitly justified.

The report must include `passed`, `failed`, and `highest_priority_gaps` counts or lists.

## Optional bounded revision

Run a revision only when the user or full AutoSciRub controller requested it and budget
remains. Perform exactly one revision per invocation:

1. Select failed criteria in priority order.
2. Write a round-specific revision plan.
3. Add missing analyses or comparisons, regenerate evidence, strengthen supported
   explanations, or remove unsupported claims.
4. Record changed artifacts and remaining gaps.
5. Return to verification; a changed file is not proof that a criterion now passes.

Do not broaden the research objective beyond failed criteria. If a gap cannot be solved
with visible data or tools, report the limitation instead of fabricating evidence.

## Relationship to Router verification

This skill evaluates scientific adequacy against the executable rubric. Always run the
Router's general `verification-before-completion` checks separately for commands, exit
codes, tests, file presence, and the final completion claim.

Adapted from [zjunlp/AutoSciRub](https://github.com/zjunlp/AutoSciRub), MIT licensed.
