# Targeted repair

Inspect each candidate against all originals. Accept anchor before dependent portraits/front, and front before profile/back/details. Record first-pass, repaired, unresolved, or missing-reference outcomes.

For clothing, select the original outfit by index and change only the failed garment region. For a wrong eye, retain the emotion and correct only viewer-relative eye states. If needed, inspect and measure fresh percentage coordinates for both eye centers. Never mirror the image. For crops, request topmost hair/ears through chin/upper neck, face/hair 80–90%, only a narrow neckline edge. Reject chest, torso, upper arms or busts.

For footwear count exactly two, one left/one right, both straight front; any inset, duplicate, side/rear/sole view fails. For proportion drift use the accepted front as a guide; matching silhouette tops/soles cannot certify anatomy. Disclose minimally inferred hidden design.

Attach all originals then the actual failed target. Use `--asset repair --guide <failed.png> --instruction-file <one-change.txt>` with a new output filename. Make one targeted change per call; retain failed versions, compare predecessors, and allow at most two quality retries per asset. Recheck dependents when anchor/front changes. NORMAL is always an unchanged copy of the accepted anchor.

On OOM retain history. Let other work finish, then adjust case-specific reference resolution/cache settings with disclosure. Keep originals attached; never silently swap models or interrupt another job.

## Local correction without global degradation

In the 2026-10-15 angel-reference case, the first front incorrectly replaced shorts with a skirt. A targeted Qwen edit restored the shorts but introduced skin/line texture elsewhere. Compositing only the generated corrected garment into the cleaner first candidate preserved unaffected source pixels. Use the bundled composite_region.py after visual inspection; no generative fallback is involved. Cover both old and new silhouettes, including removed garment corners; a box covering only the new shorts leaves old skirt edges. Keep all inputs, masks and hashes, and reject visible seams. This observation is case-specific, not evidence of repeat-run stability.

Run `python -B -m unittest discover -s scripts -p "test_*.py" -v`. Verify each real composite separately. Code tests, successful submission and geometry checks do not establish likeness or repeated-run stability.
