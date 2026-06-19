---
name: beautiful-html-templates
description: Reusable HTML slide template library with 34 complete visual systems. Use when the user wants a beautiful HTML slide deck, presentation, PPT-style web deck, pitch deck, talk slides, or template-driven slide design and wants the agent to pick, preview, clone, and adapt a strong template from a curated gallery.
---

# Beautiful HTML Templates

Use this skill to build finished HTML slide decks from the
`beautiful-html-templates` library.

Source repository: `https://github.com/zarazhangrui/beautiful-html-templates`.

## Workflow

1. Read `AGENTS.md` at the start of any deck-building task.
2. Read `index.json` to match the user's occasion, mood, tone, formality,
   density, and light/dark preference against the template catalog.
3. Shortlist three visually distinct templates.
4. For each shortlisted template, read only that template's `template.html`,
   create a real title-slide preview with the user's deck topic, and open the
   preview for the user.
5. After the user chooses, copy the selected template folder from `templates/`
   into the user's workspace and replace placeholder text, numbers, images,
   dates, author names, and chrome labels with the user's real content.
6. If the deck needs a missing layout, extend the chosen template's design
   system instead of mixing in another template.
7. Open the final deck in the browser and report the absolute path.

## Key Files

- `AGENTS.md` - operating manual for matching, previewing, and adapting templates.
- `index.json` - structured catalog of all templates.
- `templates/<slug>/` - complete template folders.
- `screenshots/` - gallery previews for template evaluation.

## Guardrails

- Preserve the chosen template's fonts, palette, layout grid, slide classes,
  decorative vocabulary, and navigation runtime.
- Do not recolor or substitute fonts unless the user explicitly asks for a
  custom redesign.
- Do not combine slides from different templates; extend one chosen visual
  system when additional layouts are needed.
- Always use real user-facing slide content in previews. Do not render internal
  labels such as "template", "option", "preview", paths, or workflow notes on
  the slide itself.
