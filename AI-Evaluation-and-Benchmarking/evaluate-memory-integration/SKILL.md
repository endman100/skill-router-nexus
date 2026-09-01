---
name: evaluate-memory-integration
description: Evaluate long-term conversational memory by comparing Direct QA retrieval with Natural Integration and fact-level Reference on the same context. Use when designing or reviewing memory benchmarks, testing whether an assistant naturally uses prior conversation, diagnosing retrieval-integration gaps, or applying the MemUse method.
---

# Evaluate Memory Integration

Evaluate whether a conversational system can notice a natural memory cue and use the relevant prior context in its response. Do not treat Direct QA accuracy alone as evidence that memory works in conversation.

## Core distinction

- **Direct QA:** Ask explicitly for a fact from prior dialogue. This measures elicited retrieval.
- **Natural Integration:** Present a natural user cue and judge whether the response demonstrates memory of the referenced topic.
- **Reference:** Check which ground-truth facts actually appear in the natural response.

Use all three metrics on the same reconstructed context. Their disagreement identifies whether the bottleneck is retrieval, cue detection, or response generation.

## Workflow

1. Collect longitudinal conversations and preserve session boundaries, timestamps, memory context, and any user feedback.
2. Detect memory moments with explicit conversational signals:
   - user probes, such as asking whether the assistant remembers something;
   - user re-provisions, such as restating information mentioned earlier;
   - system proactive recalls and user reactions, when timing risk is also being studied.
3. Verify each candidate against the source conversation. Record the trigger, referenced prior content, and why they are linked.
4. Build the replayable benchmark from user-cued reactive moments. Exclude proactive recalls from the main comparison because they do not have one canonical next response.
5. Extract ground-truth facts for each instance and turn them into 3–5 direct fact questions.
6. Replay the original user trigger through every candidate memory system while holding the generator, prompt, and reconstructed context as constant as possible.
7. Ask the direct questions separately using the same model and context.
8. Score Natural Integration per instance, Direct QA per question, and Reference per question.
9. Compare the metrics overall and by event type, user, session, model, and memory condition.
10. When user ratings or task outcomes exist, aggregate metrics to the same unit before testing their association with user experience.

## Scoring guidance

Judge Natural Integration as a reader-level yes/no question: does the response demonstrate memory of the topic the user referenced?

Judge Direct QA and Reference against individual ground-truth facts. Accept faithful paraphrases, but reject invented details and generic acknowledgements.

Interpret common patterns as follows:

- High Direct QA with low Reference: the information is available but not naturally used.
- High Natural Integration with low Reference: the response sounds memory-aware but lacks concrete factual support.
- High scores on all three: the system retrieves and naturally uses the relevant details.

Track failure modes separately: generic response, fabricated recall, gist-only recall, and honest non-recall.

## Reporting constraints

- Report Direct QA, Natural Integration, and Reference together; do not collapse them into one score.
- Keep proactive recall separate from reactive integration. Evaluate proactive recall for grounding and timing because an accurate but mistimed callback can harm the interaction.
- Calibrate the Natural Integration judge with humans and test judge strictness. Recall-style wording alone must not count as factual integration.
- State whether all systems already receive summaries; capacity results above a shared summary baseline do not measure the value of memory as a whole.
- Treat explicit-cue detection as a lower bound on memory demand because implicit memory moments are missed.
- Do not make causal claims from observational links between integration and satisfaction.

## Sources

- Paper: [MemUse: Moving Memory Evaluation from Direct QA to Natural Integration in Long-Term Human-AI Conversation](https://arxiv.org/abs/2608.24189)
- Original repository: [ryuichi-sumida/memuse](https://github.com/ryuichi-sumida/memuse)
