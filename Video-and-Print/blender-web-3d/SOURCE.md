# Upstream source and selection

- Repository: https://github.com/czlonkowski/blender-web-3d-skill
- Commit: `858762f1add7f1d9f5dcb1fb1d0b55f71906bf0d` (2026-09-23).
- Original directory: [`plugins/blender-web-3d/skills/blender-web-3d`](https://github.com/czlonkowski/blender-web-3d-skill/tree/858762f1add7f1d9f5dcb1fb1d0b55f71906bf0d/plugins/blender-web-3d/skills/blender-web-3d).
- License: [MIT](LICENSE), copyright 2026 Romuald Członkowski / AiAdvisors. Copied unchanged from the repository root.
- Import date: 2026-11-13. The complete skill directory (instructions, references, scripts and runnable viewer assets) is copied verbatim. This source note and the root license are the only added files. Repository-level README showcase media and plugin configuration are outside the imported directory.

## Candidate evaluation

Snapshot from public GitHub repository metadata and pinned source on 2026-11-13. Stars indicate adoption, not verified correctness. Last commit dates below reflect source history, rather than README claims of verification.

| Candidate | Stars | Latest inspected commit / maintenance | License | Fit and decision |
| --- | ---: | --- | --- | --- |
| [ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) (redirect from `ahujasid/blender-mcp`) | 34,269 | `8f40787fbde8e6d8fe51c5a3553e5635fff40d2b`, 2026-11-13; active code and integration updates | MIT | Strong adoption and live agent control through an MCP server plus running Blender add-on. No native `SKILL.md` at this revision. Extra service/add-on setup is unnecessary for reproducible `blender -b -P` previs; linked as an optional live-control alternative, not vendored. |
| [taosiuman/blender-skill](https://github.com/taosiuman/blender-skill) | 0 | `9ad39142e9ce5fc1962996e19f751c21516ab754`, 2026-11-12; frequent documentation updates | Apache-2.0 | Native `blender-mcp` skill, but the current instructions require Blender 5.1+ and an official Lab add-on, with a separate third-party PyPI route. Not a fit for the local Blender 4.5.3 or a service-free bpy workflow; not imported. |
| **[czlonkowski/blender-web-3d-skill](https://github.com/czlonkowski/blender-web-3d-skill)** | **6** | **`858762f1add7f1d9f5dcb1fb1d0b55f71906bf0d`, 2026-09-23; three visible commits, latest release adds runnable assets** | **MIT** | **Selected. Explicit Blender 4.x/5.x compatibility; headless CLI is the default, with bpy/bmesh, repeatable edit scripts, rendering and visual checks. Usable by Codex through its shell even though the prose addresses Claude. Smaller adoption and slower updates than the MCP project; some bundled rendering examples target 5.x, so use version-appropriate bpy for 4.5.3.** |
| [EL4CTEO/blender-skills](https://github.com/EL4CTEO/blender-skills) | 1,038 | `389f28addc79b87b28764898e38e7bf408d14b77`, 2026-11-07; recent releases and QA fixes | MIT | Explicit Codex support, strong native headless/MCP skills and bundled scripts, but `blender-core` requires Blender 5.2+. Not selected for the existing 4.5.3 binary. |
| [MartinRapcan/blender-claude-skill](https://github.com/MartinRapcan/blender-claude-skill) | 3 | `70f45e3f722e6fb7142cdeb4414891ed701dc325`, 2026-10-25; recent detailing additions and CI tests | MIT | Focused bpy/headless skill, but current instructions target 5.0–5.2 and explicitly assert version >= 5.0. Not selected for 4.5.3. |
| [kajisho5/blender-skill](https://github.com/kajisho5/blender-skill) | 2 | `fad904db54780c6db624a71d2cada45235d2e7c0`, 2026-11-12; active tooling and CI changes | MIT | Supports 4.2+ and headless asset conversion, optimization and rendering. Explicitly forbids handwritten bpy fallbacks outside its fixed tools; less suitable for generating a new animated cube previs from a shot script. |

TanLuAI did not identify a specific skill in [the reference post](https://x.com/TanLuAI/status/2117952600553529475). This is an independently selected equivalent, not an attribution to the author.

## Router use

- `KEEP_FLAT`: `Video-and-Print` already covers 3D model work; it has 11 skills after import and does not need a new category or taxonomy branch.
- Related method: [video-to-whitemodel-previz](../../Video-Understanding/video-to-whitemodel-previz/SKILL.md), restored with `git restore --source=6329b032` from `6329b0324ff1e64e6fc189a5747744b38570782e` and extended with quick-draft mode. `Video-Understanding` has 4 skills after restoration and also remains flat.
- For that method, use this skill's headless scripting guidance and neutral cube geometry. The web viewer, GLB optimization and deployment portions are for tasks that actually request those outputs.
- Local executable: `/workspace/whitemodel/tools/blender-4.5.3-linux-x64/blender`. Use `-b --factory-startup --python-exit-code 1 -P scene.py`. Do not run the bundled 5.x `render_beauty.py` unchanged on 4.5.3; its EEVEE ID and compositor API differ. No Blender upgrade, MCP service, external API or Node.js installation is needed for the previs method.

## Import verification

- All 28 files in the imported directory match the pinned upstream Git blob hashes; the upstream license is preserved.
- `python3 skill_reader.py --validate` and validation scoped to both affected categories: `VALID`. Exact scoped queries discover both skill names.
- Blender 4.5.3 smoke checks: the unmodified `demo_station.py` builds and saves 25 objects / 32,964 triangles; a temporary white-cube bpy script saves a `.blend` and renders two animated PNG frames using `-b --factory-startup --python-exit-code 1 -P` and Cycles CPU. Generated files stay outside the router.
- The local ancillary Codex `quick_validate.py` accepts the previs skill but rejects the upstream `compatibility` frontmatter field under its smaller allowed-key list. That field is retained verbatim; the repository's required validator accepts the import. This is not a claim that every bundled 5.x example runs on 4.5.3.
