---
name: autoscirub
description: Coordinate evaluation-first scientific research by turning an underspecified instruction into an evidence-grounded executable rubric, using that rubric to guide research execution, verifying report and supporting artifacts criterion by criterion, and running bounded targeted revisions. Use for substantial scientific or AI-research tasks that produce task-generated evidence such as code, results, tables, figures, and a report; also supports explicit rubric-only mode. Do not use for simple paper lookup, summarization, generic article writing, or tasks without verifiable research artifacts.
---

# AutoSciRub

Treat the executable rubric as the contract connecting scientific intent, execution,
verification, and revision. This skill adapts the AutoSciRub workflow for
Skill Router Nexus while keeping its six method stages behind one routed interface.

## Choose a mode

- **End to end**: induce a rubric, execute the research, verify it, and revise failed
  criteria within a bounded budget.
- **Rubric only**: stop after writing `.autoscirub/executable_rubric.json`.
- **One revision round**: require an existing rubric and verification report, perform
  one targeted revision, then return to verification.
- For verification without induction, route to `autoscirub-verify` in
  `Agent-Verification`.

Do not activate this workflow merely because a task mentions a paper or research.
Require an open-ended scientific objective and inspectable task-generated evidence.

## Router integration

Load this controller as the routed skill. Read each stage reference only when that
stage is reached; do not preload all six references.

| Router phase | Internal stage | Read on demand | Output |
|---|---|---|---|
| UNDERSTAND | Rubric Skeleton Induction | `references/rubric-skeleton-induction.md` | `rubric_skeleton.json` |
| PLAN | Scientific Literature Grounding | `references/scientific-literature-grounding.md` | `literature_grounding.json` |
| PLAN | Task-Data Exploration | `references/task-data-exploration.md` | `task_data_profile.json` |
| PLAN | Criterion Synthesis | `references/criterion-synthesis.md` | `executable_rubric.json` |
| EXECUTE | Research execution | Route to the necessary domain or execution skill | report and supporting artifacts |
| VERIFY | Criterion-Level Verification | `references/criterion-level-verification.md` | `verification_report.json` |
| EXECUTE after a failed VERIFY | Targeted Revision | `references/targeted-revision.md` | revision plan, changed artifacts, change summary |

The internal references are declared workflow dependencies, not independent Router
candidates. Record every reference that was read in the lifecycle ledger.

## State contract

Use the current project as the task root. Write state under `.autoscirub/` unless
the user or environment supplies another state directory.

```text
.autoscirub/
  run_manifest.json
  rubric_skeleton.json
  literature_sources.json          # optional normalized retrieval index
  literature_grounding.json
  task_data_profile.json
  executable_rubric.json
  verification_report.json
  revisions/
    round-001/
      revision_plan.json
      change_summary.json
      verification.json
```

Keep paths relative to the task root. Do not assume fixed report, data, environment,
or output paths. Respect user exclusions and never inspect hidden answers, target
papers, private grading material, or files outside the task-visible environment.

## End-to-end procedure

1. Read only the research instruction and run Rubric Skeleton Induction.
2. Ground each goal in scientific literature and authoritative documentation.
3. Inspect visible data, code, tools, and constraints without running full experiments.
4. Synthesize a compact executable rubric with evidence and satisfaction conditions.
5. Route execution to the scientific, coding, analysis, or visualization skills needed
   to produce the requested report and supporting artifacts.
6. Verify every rubric criterion independently against generated evidence.
7. If required criteria fail and revision budget remains, run exactly one targeted
   revision round and verify again.
8. Stop when required criteria pass, the configured revision budget is exhausted, or
   an evidence gap is infeasible. Default to at most three revision rounds when the
   user has not supplied a smaller budget.
9. Run the Router's general completion verification and delivery phases. AutoSciRub's
   scientific verifier does not replace them.

## Invariants

- Derive goals from the instruction; do not smuggle methods or expected results into
  the initial skeleton.
- Use literature to design evidence, never as a substitute for task-generated evidence.
- Require only analyses feasible with visible data and available tools.
- Give criteria stable identifiers and preserve them across verification and revision.
- Prefer missing experiments, comparisons, and evidence over cosmetic rewriting.
- Do not fabricate results, labels, baselines, citations, measurements, or resources.
- Keep unsupported claims out of the final report or label the limitation explicitly.

## Completion

AutoSciRub finishes in one of two truthful states:

- all required and high-priority rubric criteria are supported by generated evidence; or
- the revision budget is exhausted with a verification report that names every remaining
  evidence gap and infeasible requirement.

The second state is not a successful research result, but it is a complete diagnostic
handoff. Let the Router's delivery skill report the final task status.

## Source

Adapted from [zjunlp/AutoSciRub](https://github.com/zjunlp/AutoSciRub), based on
*Learning to Evaluate Before Improving: Automatic Rubric Induction for Automatic
Research Agents* (arXiv:2608.31076). The upstream project is MIT licensed; see
`LICENSE` in this skill package.
