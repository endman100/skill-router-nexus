# Eye-only model reduction

Use `scripts/cmo3_eye_subset.py` as a concrete, tested reduction workflow for compatible Cubism 5 XML layouts.

The script selects ArtMeshes through Parts named `Eye` and `Eyeball`, retains the six standard eye parameters (`Eye L/R Open`, `Eye L/R Smile`, `Eyeball X/Y`), follows required deformer and Part ancestry, freezes non-eye-controlled ancestor deformers at their exact default keyforms, clears Glue/Physics/Random Pose/LIPSYNC, filters compatibility IDs, and garbage-collects unreachable shared definitions.

```powershell
python "<skill-dir>\scripts\cmo3_eye_subset.py" "source.cmo3" "eyes.cmo3" `
  --report "eyes.report.json"
```

Use repeated `--eye-part-name` options for models whose Part local names differ:

```powershell
python "<skill-dir>\scripts\cmo3_eye_subset.py" "source.cmo3" "eyes.cmo3" `
  --eye-part-name "Eye" --eye-part-name "Eyeball"
```

This is a model-graph reduction, not physical PNG pruning. It preserves all original archive entries so Cubism source/cached image resources remain available. Read [Image editing](image-editing.md) before claiming the package contains only eye image assets.

Do not apply the script blindly when parameter or Part names differ. First inventory the target model, then adapt selectors and expected parameter names. Require a fresh full dump and Cubism manual verification after generation.
