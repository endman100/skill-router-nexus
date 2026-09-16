# Vidu S2-Avatar — Voices

The current voice catalog is published at [Global voice list](https://platform.vidu.com/vidu-stream/doc/voice-list) and [China voice list](https://platform.vidu.cn/vidu-stream/doc/voice-list). Choose the **Avatar Realtime** section for the session's speech provider and region. The catalog also includes offline voices; those are not interchangeable with real-time voices. Use its listed language support rather than assuming every voice speaks the same set of languages.

For the default `qwen_omni` provider, `avatar.voice` defaults to `Tina`. Examples of system IDs include `Tina`, `Cindy`, `Liora Mira`, and `Sunnybobi`. `GET /live/v1/voices` lists the account's custom cloned voices; an empty list does not mean system voices are unavailable.

## Clone a voice

`POST /live/v1/voices/clone`, authenticated with `Authorization: Token vda_xxx`:

```json
{
  "audio_url": "https://example.com/reference.wav",
  "voice": "my_voice",
  "language": "en",
  "provider": "qwen_omni"
}
```

The current [Avatar parameters](https://platform.vidu.com/vidu-stream/doc/s2-avatar/realtime/parameters) state:

- `audio_url`: public URL or data URI; WAV (16-bit), MP3, or M4A; 10–20 seconds recommended, at most 60 seconds and under 10 MB. The field has a documented 2048-character limit, so use a public URL for longer audio.
- `voice`: unique name of 1–16 letters, digits, or underscores.
- `language` and reference transcript `text` are optional; consult the parameter page for supported language values.
- `provider`: `qwen_omni` (default) or `doubao`. Clones are bound to the provider; use the same `voice_model.provider` when creating an Avatar session. Overseas `doubao` voice cloning is not supported.

Pass the returned voice name to `avatar.voice` for its matching provider. The Node quickstart exposes voice selection for the default provider, with no cloning UI. Check current cloning charges in the official docs before creating paid clones.
