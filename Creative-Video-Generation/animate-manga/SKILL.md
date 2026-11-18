---
name: animate-manga
description: |
  Adapt existing manga pages into an animated scene with Manga2Animate. Use when the user wants to preserve the source panel order, dialogue, characters, and art style through a reviewed script and storyboard, or wants to evaluate the upstream workflow for a manga-to-video project.
---

# Animate Manga with Manga2Animate

## When to use

Use this reference when adapting a scene from existing manga pages and fidelity to
the source matters. Manga2Animate uses existing models for inference. Its script
and storyboard give the video model a shot plan that can be checked against the
original panels before rendering. For a method overview and examples, see the
[project page](https://annchenn.github.io/Manga2Animate/).

## Inputs and outputs

- Input one or more page images in reading order and character reference images.
  Upstream accepts a shared reference sheet or separate images per character.
  The published setup defaults to six target panels per case.
- Intermediate outputs include ordered panel crops, an OCR transcript, character
  descriptions, the selected clip-by-clip script, and the selected storyboard.
- The final output is an MP4. Audio depends on the video backend.

## Pipeline

1. **Read the manga.** MAGI detects and crops panels, estimates their reading
   order, and extracts dialogue with OCR. Gemini describes the characters from
   the reference images. Inspect the panel sequence and transcript for errors
   before relying on them for the script.
2. **Build the script.** Gemini generates three candidates per round by default.
   Reviewers compare character and clip descriptions against the source panels
   and references, then assemble the best parts into one script.
3. **Build and refine the storyboard.** Generate storyboard candidates from the
   selected script, original panels, and character references. Review for source
   fidelity, character identity, visual consistency, and script alignment.
   Feedback on both the script and storyboard informs the next round. The
   default is two rounds total, including the initial round. Gemini generates
   the default storyboard. FLUX.2-dev generates candidates per panel, and a
   Gemini reviewer selects each panel before the storyboard grid is assembled.
4. **Generate and select video.** Seedance 2.0 is the default. It uses the full
   storyboard and script to generate two video candidates, and a Gemini reviewer
   selects the better one. MiniMax-H3 supports the same reference mode. With
   Index-AniSora, each storyboard panel is the first frame of its clip. The
   reviewer picks the better of two candidates per clip, checking continuity
   with the preceding selection, then the chosen clips are joined.

For setup and execution, follow the upstream [pipeline instructions](https://github.com/annchenn/Manga2Animate#running-the-pipeline)
and [backend setup](https://github.com/annchenn/Manga2Animate/blob/master/opensource_backends/README.md).
The published workflow uses the Gemini API for text and review even when the
storyboard and video generation backends run locally.

## Known limits

- Generation is stochastic. Check the selected result against the manga for
  panel order, dialogue, character appearance, and continuity across shots.
- Rough artwork, crowded panels, and complex layouts can be misread. Scenes
  that depend on context from other chapters may also be misinterpreted.
- Hosted models may restrict generation for some copyrighted or policy-sensitive content.

## Sources and license

- [Manga2Animate paper, arXiv:2610.26851](https://arxiv.org/abs/2610.26851), CC BY 4.0.
- [Public upstream code](https://github.com/annchenn/Manga2Animate). The repository-wide
  code license is unknown. The paper license applies to the paper.

## Related router skills

- [seedance-storyboard-grid-to-video](../../Video-Generation/seedance-storyboard-grid-to-video/SKILL.md) for turning a storyboard grid into a Seedance video.
- [h3-storyboard](../../Video-Generation/h3-storyboard/SKILL.md) for breaking a script into MiniMax H3 shots and directing performances.
- [baoyu-comic](../../Image-Generation/baoyu-comic/SKILL.md) for creating original educational comics.
- [3d-animation-short-generator](../3d-animation-short-generator/SKILL.md) for developing an original story idea into a stylized 3D animated short.
