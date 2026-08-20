---
name: video-use-install
description: Install the content-system video-use variant with ASR Router word timestamps.
---

# video-use install

This workspace uses a local variant of `browser-use/video-use`. Editing logic,
EDL rendering, cut-boundary checks, and timeline views remain upstream-compatible;
speech recognition delegates to the installed `asr-router` skill.

## Requirements

1. The complete skill directory, including `helpers/`, is discoverable by the agent.
2. `ffmpeg` and `ffprobe` are on `PATH`.
3. Python dependencies from `pyproject.toml` are installed.
4. `asr-router` is discoverable by the Agent.
5. Configure provider credentials according to the selected router method.

## Install and registration

The project copy under `.claude/skills/video-use/` is the source of truth.
Run the workspace sync script after updating it:

```bash
bash automation/scripts/sync_skills.sh
```

For global discovery, link the project source of truth into each agent's skill
directory. Do not link an unmodified upstream checkout because it still uses a
different transcription provider.

## Dependency setup

```bash
cd <WORKSPACE>/.claude/skills/video-use
UV_PROJECT_ENVIRONMENT=<HOME>/.venvs/video-use uv sync
ln -sfn <HOME>/.venvs/video-use .venv
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
```

`yt-dlp` remains optional and is only needed for URL downloads. Animation
engines are installed lazily inside the individual animation slot.

## Readiness check

```bash
.venv/bin/python helpers/transcribe.py --doctor
.venv/bin/python helpers/timeline_view.py --help >/dev/null
ffprobe -version | head -1
```

The helper doctor confirms only that video-use consumes Router results rather
than executing a provider. Check the selected ASR method through `asr-router`
itself. A real recognition test should use a short genuine speech clip;
synthetic silence is not a valid ASR check.

## Daily use

Read `SKILL.md` and all helper descriptions. Put raw footage in its project
folder; all outputs stay under `<videos_dir>/edit/`. The Agent invokes
`asr-router` for each uncached source, then imports the normalized result with
`helpers/transcribe.py --asr-result`. Transcripts must not be regenerated unless
the source changes.
