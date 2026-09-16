# Vidu S2 — HTTP Reference

Sources (checked 2026-09-14): [overview](https://platform.vidu.com/vidu-stream/doc), [Avatar parameters](https://platform.vidu.com/vidu-stream/doc/s2-avatar/realtime/parameters), [Editing parameters](https://platform.vidu.com/vidu-stream/doc/s2-editing/parameters). For China, replace `platform.vidu.com` with `platform.vidu.cn`.

Use `https://api.vidu.cn` or `https://api.vidu.com` with the matching regional key. Normalize `vda_xxx` to `Authorization: Token vda_xxx`. Send JSON over HTTP and keep the key on the server. Creation paths below match the overview and S2 quickstarts.

## Avatar

`POST /live/s_avatar/realtime`

```json
{
  "call_mode": "video",
  "character_id": "1",
  "avatar": {
    "image_uri": "https://example.com/character.png",
    "persona": "You are a friendly digital character. Respond naturally to the user.",
    "name": "Tina",
    "voice": "Tina",
    "persona_enhance": false
  }
}
```

| Field | Meaning |
|---|---|
| `call_mode` | Required: `audio` or `video` |
| `character_id` | The supplied demo sends `"1"`; preserve as a string |
| `avatar.persona` | Required in this image-based flow; up to 50,000 characters |
| `avatar.image_uri` | One single-person image; public URL or base64 data URI. PNG/JPG/JPEG/WEBP; URL image ≤50 MB, base64 decoded size <20 MB |
| `avatar.name` | Optional display name used by the supplied demo |
| `avatar.voice` | Optional, defaults to `Tina`; see [voices](voices.md) |
| `avatar.persona_enhance` | Boolean, default false; the demo exposes it for video mode |

The docs additionally support an uploaded `avatar.id` in place of `image_uri`, voice-model configuration, memory, and other options. Read the official parameter page when those features are requested; they are outside the minimal Node demo.

Creation returns `{ "live": { ... }, "rtc": { ... } }`:

- `live.id`: string session ID for WS and later queries.
- `live.status`: initially `waiting`; creation alone does not mean rendering is ready.
- `live.live_duration`: session duration cap in seconds.
- `rtc.app_id`, `rtc.channel_id`, `rtc.user_id`: RTC identities.
- `rtc.token`: base64 join credential for `joinChannel(rtc.token, rtc.user_id)`.
- `rtc.token_expire_at`: Unix expiry time in seconds, commonly encoded as a string.

`GET /live/v1/lives/{live_id}` returns `{ "live": { ... } }`, including status, `billed_seconds`, `credits_cost`, timestamps, and `trace_id`. States include `waiting`, `prepared`, `on_live`, `ending`, and `ended`.

## Editing

`POST /live/s_editing/realtime`

```json
{
  "image_url": "https://example.com/reference.png",
  "editing_type": "style_transfer"
}
```

`image_url` is required. Accepts an HTTP(S) URL, base64 image data URI, or platform upload URI (`ssupload:?id=...`). The reference demo limits local files to 4 MB; base64 expands them to about 5.4 MB, so size both HTTP and WS proxy limits accordingly.

| `editing_type` | Reference image supplies |
|---|---|
| `style_transfer` (default) | Desired visual style |
| `virtual_tryon` | Clothing |
| `subject_replacement` | Replacement character/subject |
| `background_replacement` | Background |

Response includes `live`, `rtc`, and **`render_uid`**. If `client_secret` is returned, retain it for the upstream WS query. Do not assume it is always present; current response examples vary. `render_uid` identifies the edited output's camera stream; other RTC users' video is not the editing result.

Use `live.live_duration` and `rtc.token_expire_at` from the response. The demo supports camera input and runtime `switch_prompt`. RTMP relay and local video-file input are documented API options but are not part of this demo.

## Billing and errors

Current official pricing: Avatar Real-time **3 credits per 2 seconds**, rounded up to an even number of seconds; Editing **1 credit per second**. Billing starts at `on_live` (`conn_init_ack.success=true`) and ends with the session. Switching an Editing reference is not charged separately. Check the official docs for current account limits and pricing rather than copying currency conversions.

Avatar docs state a maximum session duration of 7200 seconds and a minimum balance of 45 credits to start; use returned per-session values for runtime behavior. Editing limits may differ, and insufficient credits or concurrency limits can reject creation. An insufficient balance can end a running session.

On HTTP failure, inspect the status and `message`/`reason` (or `error.message`). Use `trace_id` when reporting failures. A 401/403 commonly means a bad key, wrong region, or inaccessible session. A 400 can indicate invalid input or insufficient credits; a 429 indicates a concurrency limit. Avoid interpreting every 400 as an authentication error.
