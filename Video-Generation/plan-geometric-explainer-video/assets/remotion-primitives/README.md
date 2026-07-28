# Remotion calibration primitives

These components come from the verified 27-second reconstruction of source video V00 at [01:49–02:16](https://www.youtube.com/watch?v=aR97E7aKEgg&t=109s). Use them as a starting point for that target segment, not as evidence that every channel video uses the same pixel values or spring configuration.

| Component | Observed source interval | Bundled image |
|---|---|---|
| `ChapterHeader.tsx` | persistent throughout V00; phase 02 visible in the calibration segment | `../reference/motion/04_pipeline_nodes.png` |
| `CaptionBar.tsx` | persistent bottom subtitle treatment | `../reference/implementation/Remotion-vs-Original-Comparison-Preview.png` |
| `FrameworkCard.tsx` | [01:49–01:55](https://www.youtube.com/watch?v=aR97E7aKEgg&t=109s) | `../reference/implementation/Remotion-vs-Original-Comparison-Preview.png` |
| `StepPipeline.tsx` | [01:55–02:04](https://www.youtube.com/watch?v=aR97E7aKEgg&t=115s) | `../reference/motion/04_pipeline_nodes.png`, `../reference/motion/05_error_propagation.png` |
| `ModuleGrid.tsx` | [02:07–02:10](https://www.youtube.com/watch?v=aR97E7aKEgg&t=127s) | `../reference/motion/06_modules_converge.png` |

The exact values in these files are implementation calibration values. When adapting another scene, preserve the observed semantic behavior—scaffold first, focus, state mutation, annotation—then remeasure the geometry from that scene's cited frame.
