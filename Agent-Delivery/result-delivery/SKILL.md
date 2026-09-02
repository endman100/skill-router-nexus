---
name: result-delivery
description: Structure final user-facing task delivery after execution and verification. Use in every DELIVER phase to present the outcome first, expose artifacts and verification evidence, distinguish completed, partial, and blocked states, and keep the response readable and self-contained.
---

# Result Delivery

Read the task request, lifecycle routing ledger, produced artifacts, verification evidence, and unresolved gaps before writing the final response.

## Set the status

Choose exactly one status:

- `COMPLETED`: Every required outcome exists and fresh verification supports the completion claim.
- `PARTIAL`: Some useful requested outcomes exist, while named requirements or checks remain incomplete.
- `BLOCKED`: A missing input, capability, permission, dependency, or failed check prevents a usable requested outcome.

Never upgrade `PARTIAL` or `BLOCKED` based on confidence. Report the state supported by evidence.

## Write in this order

1. Lead with the outcome and status in plain language.
2. Present the requested answer or artifacts. Link local files with absolute paths and web resources with descriptive Markdown links; show media previews when the client supports them.
3. Summarize fresh verification evidence, including commands or sources and the observed result.
4. State gaps and the next required action only when something remains unresolved.
5. End with the Router's per-stage skill source report.

For a short answer, merge compatible sections into one or two paragraphs. Keep the same information order.

## Keep it readable

- Make the final response self-contained; do not require the user to reconstruct it from progress updates.
- Prefer concise prose. Use headings, bullets, tables, or diagrams only when they make the result materially easier to scan.
- Separate verified facts from inferences and recommendations.
- Report relevant evidence, not raw logs or hidden reasoning.
- Name limitations directly and avoid language that implies unverified success.

## Completion criterion

Finish when the user can identify the true status, obtain the requested result or artifact, see what was verified, understand any remaining gap, and trace which skills governed each lifecycle stage.
