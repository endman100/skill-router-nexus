# Versioned prompts

Use the prompt-pack repo txt files as the single source of generation prompts:

- [Sheet prompts](https://github.com/endman100/character-sheet-prompt-pack/tree/main/prompts/sheet): cutout, front, profile, back, details, HAPPY, ANGRY, and neutral anchor.
- [Expression prompts](https://github.com/endman100/character-sheet-prompt-pack/tree/main/prompts/expr): one PNG per txt; the txt files are the expression inventory.
- [Action prompts](https://github.com/endman100/character-sheet-prompt-pack/tree/main/prompts/actions): one PNG per txt, normally at 2:3.

Run the repo scripts from the repo root as shown in SKILL.md. Update prompts there when a transformation changes; do not maintain another template set here. Original images supply identity. Text specifies the requested transformation, framing, native alpha, emotion, and viewer-relative eye action; do not add inferred facial anatomy or numerical age.
