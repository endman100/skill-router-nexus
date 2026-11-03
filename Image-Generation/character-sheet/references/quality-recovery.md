# Visual review and recovery

Review source assets and the final sheet against the original references. Passing source hashes, alpha checks, and geometry does not establish likeness or expression accuracy.

Check clothing continuity, tight headshot crops, clear emotion and viewer-relative eye state, exactly two front-facing feet/shoes, and native transparency including interior holes and translucent edges. NORMAL must remain byte-identical to the accepted neutral anchor.

When an asset fails, correct the relevant repo prompt/input and rerun the necessary pipeline stage. The default skips existing valid files; use `--force` only when every output in the selected stage may be regenerated. Keep retry prompts and ordered references in the repo JSONL logs. Limit quality retries to two per failed asset and report unresolved defects.

For layout defects, reuse accepted source assets and run the repo compositor/verifier; no generation call is needed. Record first-pass failures separately from repaired results. A repaired example does not establish repeat-run stability.
