---
name: vidu-s-api
description: "Integrate Vidu S2-Avatar real-time digital characters and Vidu S2-Editing live video editing. Use for Vidu S session creation, Aliyun RTC media, control WebSocket initialization, text instructions, runtime reference-image changes, voice selection, and session cleanup."
---

# Vidu S API — S2

Upstream skill: [shengshu-ai/vidu-s-api](https://github.com/shengshu-ai/vidu-s-api/tree/main/skills/vidu-s-api). Use the official regional documentation linked below for current product capabilities, limits, and pricing.

Use the user's selected region: China uses `api.vidu.cn`, Global uses `api.vidu.com`. Keys are region-specific. Ask for the region only when it is unknown and a live call or region-specific configuration depends on it.

Official documentation: [China](https://platform.vidu.cn/vidu-stream/doc) · [Global](https://platform.vidu.com/vidu-stream/doc). Use these for current product capabilities, limits, and pricing. The repository's Node quickstart implements Avatar Real-time and Editing Real-time. For Avatar Component (bring your own ASR/LLM/TTS/RTC) or Offline generation, read the corresponding official docs instead of applying the real-time session flow below.

## Select the flow

- **Avatar**: create with `POST /live/s_avatar/realtime`, a character image, persona, and `call_mode`. Read [HTTP reference](references/api-reference.md#avatar) for payloads and [voices](references/voices.md) when selecting or cloning a voice.
- **Editing**: create with `POST /live/s_editing/realtime`, a reference image and `editing_type`. Read [HTTP reference](references/api-reference.md#editing) for payloads and the rendered stream's identity.

Both use server-side `Authorization: Token vda_xxx` for HTTP and upstream WS. Keep the API key on a trusted server; proxy browser control messages. The optional Editing `client_secret` returned by creation can remain on that server too.

Treat live IDs as strings. Retain the returned `live`, `rtc`, and (Editing only) `render_uid`. Read the returned duration and token expiry for each session.

## Start and maintain a session

1. Create the chosen session over HTTP.
2. Open `/live/ws/live/connect?live_id=...&conn_id=...` through the server, including Editing `client_secret` when returned. Send `conn_init` immediately. Read [WebSocket protocol](references/websocket-protocol.md) before implementing the handshake, retries, or runtime signals.
3. In Avatar video and Editing, wait for `conn_init_ack.success=true`, then join Aliyun RTC. Avatar audio can join while control initialization is pending.
4. For Aliyun Web SDK 7.1.9, call `joinChannel(rtc.token, rtc.user_id)`, using the returned base64 credential directly. Configure the `communication` channel profile and subscriptions before joining. Vidu supplies credentials; a browser AppKey or self-generated token is unnecessary. Web SDK 7.1.9 has no `setDefaultPublishLocalAudioStream` or `setDefaultPublishLocalVideoStream`; use its `publishLocal*Stream` methods after joining, and `setAudioOnlyMode(true)` for Avatar audio mode.
5. Publish microphone audio; publish camera video for Avatar video and Editing. Bind remote video when subscription state is `3` (subscribed): `videoSubscribeStateChanged` corresponds to camera stream type `1`, and `screenShareSubscribeStateChanged` to screen stream type `2`. For Editing, display only **`render_uid`'s camera stream**. For a single Avatar result view, select the Vidu publisher with a `live-bot-*` or `live-video-push-*` user ID and pass the event's stream type to `setRemoteViewConfig`; unrelated RTC participants must not replace the generated output.
6. Keep the upstream WS heartbeat alive. The Node `ws` client replies to ping frames automatically. `authInfoWillExpire` is an advance warning: log or surface it while keeping the current call active. Release media on `authInfoExpired`, the actual `rtc.token_expire_at` deadline, `type: 6`, or WS close/error. Guard callbacks against events from ended sessions.
7. On hangup, send `type: 5`, close WS, stop preview, leave RTC, and destroy the engine. A newly created session must use fresh credentials.

The Node demo exposes Avatar text instructions and Editing reference/scenario changes. The documented Avatar reference-image operation is separate from Editing `switch_prompt`; use the correct signal when a user requests that capability.

## Source differences

The official overview and supplied S2 quickstarts use `/live/s_avatar/realtime` and `/live/s_editing/realtime`. Some detail pages still show the older generic creation paths and different Editing authentication examples. Use the named S2 routes and header authentication used by the supplied S2 proxy; do not switch endpoints or expose the API key in browser URLs to follow a conflicting snippet. For Editing `NOT_READY`, current detail docs specify an automatic success ack; Avatar retries `conn_init` on the existing socket after 2–3 seconds. Bound startup waiting (the demo uses 60 seconds for Avatar and 120 seconds for Editing).

For an online trial, use `https://www.vidu.cn/vidu-stream` or `https://www.vidu.com/vidu-stream` for the user's region.
