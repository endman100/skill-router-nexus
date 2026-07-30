# Technical Short review rubric

Review the draft in this order. Identify the exact sentence and a local correction for every failure.

## 1. Readability

- Can each sentence be understood on first hearing?
- Break up dense lists and long clauses.
- Remove repeated claims, filler transitions, and unexplained abbreviations.
- Keep the speaking rhythm natural; do not sound like a specification table.

## 2. Ordinary-reader comprehension

- Define the topic before describing internal components.
- Explain unfamiliar English terms briefly at first mention. Anchor each term in what it does or changes.
- Reject noun-with-noun explanations. If understanding one term requires another unexplained term, rewrite it as an observable action or effect, or remove the detail.
- Use one concrete effect or use case when it clarifies the technology, but do not expand into a tutorial.
- Replace formulas or parameter inventories with the capability they create unless the mechanism requires them.

## 3. Previous-version difference

- When a direct predecessor exists, compare the predecessor and current version on the same task, input, or condition.
- State the comparison as `previous behavior → current behavior → practical consequence`. Replace claims such as `quality is better` with the visible change.
- Use one concrete before-and-after example when it helps the listener picture the difference. Keep it accurate and short.
- When no direct predecessor exists, compare with the earlier common method and label the comparison narrowly. Never invent a predecessor.

## 4. Technical clarity

- Verify names, dates, versions, capacities, latency, prices, and comparison numbers against primary sources.
- Introduce each mechanism as `problem or effect → name → operation or specification`.
- Keep a mechanism only when it explains the version difference, limitation, or practical consequence. If it needs more than two concise sentences of new terminology and is not essential, omit it.
- Separate supported facts from inference; qualify environment-dependent performance.
- Explain comparison numbers in terms of the real capability they measure without naming a benchmark suite.
- Include at least one meaningful limitation or trade-off.

## 5. Natural language and AI-shell scan

- Read [anti-ai-language.md](anti-ai-language.md) and remove every hard-ban pattern from the spoken body.
- Replace vague referents with exact nouns and vague comparatives with a named version, task, and changed behavior.
- Remove abstract pressure, slogan endings, and transitions that merely announce importance.
- Confirm that the script sounds like a person describing observed differences, not a lesson outline or product launch copy.

## 6. Adjacent-sentence continuity

- Confirm every pronoun has an obvious referent.
- Make each sentence answer or extend the sentence before it.
- Introduce a new paragraph with a bridge from the previous idea.
- Reorder sentences when a mechanism, number, or conclusion appears before its cause.
- Check that the ending follows naturally from the stated strengths and limitations.

## Correction rule

Modify only failed sentences and the minimum surrounding transitions. Preserve the draft's valid structure, facts, and voice. Run the full rubric again after every correction. Do not replace the whole script merely because one paragraph fails.
