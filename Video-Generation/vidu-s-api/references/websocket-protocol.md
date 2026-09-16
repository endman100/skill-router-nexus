# Vidu S2 — WebSocket Control

Sources: official [Avatar parameters](https://platform.vidu.com/vidu-stream/doc/s2-avatar/realtime/parameters) and [Editing parameters](https://platform.vidu.com/vidu-stream/doc/s2-editing/parameters), checked 2026-09-14. The matching China pages use `platform.vidu.cn`.

## Connection and envelope

```text
wss://{host}/live/ws/live/connect?live_id={live_id}&conn_id={conn_id}
Authorization: Token vda_xxx
```

Use `api.vidu.cn` or `api.vidu.com`. The trusted server authenticates the upstream connection. Append `client_secret` for Editing when creation returned it. Generate one `conn_id` per control connection and use it consistently in the URL and signals. Keep `live_id` as a string and increment `seq_id` for each signal.

```json
{
  "type": 1,
  "live_id": "995200676634042368",
  "conn_id": "client-generated-uuid",
  "seq_id": 1,
  "payload": { "conn_init": { "version": 1 } }
}
```

WebSocket carries control JSON. Camera, microphone, and rendered media use AliRTC.

| Type | Direction | Payload |
|---|---|---|
| 1 | Client → server | `conn_init` |
| 2 | Server → client | `conn_init_ack` |
| 5 | Client → server | `hangup` |
| 6 | Server → client | `hangup` (forced termination) |
| 99 | Client → server | Avatar `text_msg` |
| 11 / 12 | Request / ack | Avatar `prompt_operation` / `prompt_operation_ack` |
| 13 / 14 | Request / failure ack | Editing `switch_prompt` / `switch_prompt_ack` |

## Initialization and heartbeat

Send `type: 1` immediately after WS open. A TCP/WS connection is not readiness. Read `payload.conn_init_ack` on `type: 2`:

- `success: true`: control is ready; billing starts. Video/Editing can now join RTC.
- `error_code: NOT_READY`: renderer is warming up. Avatar resends `conn_init` on the **same socket** after 2–3 seconds. Editing's current docs specify that the server automatically sends success when ready; keep waiting on that socket.
- Other failure, including `LIVE_CONN_INIT_FAILED`: end this attempt and create a new session. Surface `error_msg` and `error_code` for troubleshooting.

Bound initialization waiting. The Node demo uses 60 seconds for Avatar and 120 seconds for Editing. Clear pending retry/deadline timers on success or termination.

The client must maintain the upstream heartbeat; Avatar docs specify traffic within 15 seconds. Node `ws` automatically replies to server ping frames. A healthy browser-to-proxy socket alone does not establish upstream health.

## Avatar text

Send `type: 99` with this payload after readiness:

```json
{
  "text_msg": {
    "msg_id": "unique-message-id",
    "content": "Introduce yourself, then wave to me.",
    "timestamp": 1789000000000
  }
}
```

`timestamp` is in milliseconds. There is no separate business ack. The reply is rendered through RTC; some text responses can also arrive through WS. The public protocol also defines `type: 7` with an empty payload for interrupting current AI output, without a separate ack; the minimal Node demo does not expose that control.

## Avatar reference-image operation

This documented capability is separate from Editing's signal and is not exposed in the minimal Node demo. Send `type: 11`:

```json
{
  "prompt_operation": {
    "op_type": "switch",
    "image_uri": "https://example.com/blue-mug.png",
    "scene_type": "object",
    "content": "Hold this blue mug."
  }
}
```

`image_uri` accepts HTTP(S) URLs. Optional `scene_type` is `object`, `garment`, or `background`; omission lets the system determine the scene. `content` is optional. To clear the reference use only `{ "prompt_operation": { "op_type": "remove" } }`. Read `type: 12` → `payload.prompt_operation_ack.success/error_code/error_msg`. Visual changes take a few seconds. A model-unsupported error means the session is not using the required S2 model; preserve that error instead of treating it as success.

## Editing image/scenario switch

Send `type: 13` with:

```json
{
  "switch_prompt": {
    "prompts": [{ "type": "image", "content": "https://example.com/outfit.png" }],
    "editing_type": "virtual_tryon"
  }
}
```

At most one image prompt. Its content accepts the same formats as creation's `image_url`. Supply `prompts`, `editing_type`, or both; an omitted field retains its current value. An empty operation does nothing.

**Success has no ack.** On failure, `type: 14` contains `payload.switch_prompt_ack` with `success: false`, `error_code`, and `error_msg`. Signals are not deduplicated: send each user-requested change once. Never retry a switch solely because it has no acknowledgement. After correcting a reported failure, a new user-requested attempt uses a fresh `seq_id`.

## Ending and cleanup

Send `type: 5` with `{ "hangup": { "hangup_reason": "user_end" } }`, then close WS, stop preview, leave RTC, and destroy the engine. Also release media when the server sends `type: 6`, WS closes/errors, or RTC credentials expire. Prevent late callbacks from an ended session from changing the current UI or media.

Forced hangup reasons include `timeout`, `credit_insufficient`, `audit_violation`, `provider_closed`, `sip_closed`, and reconnect timeouts. Surface the supplied reason; the set may expand. Treat a missing `type: 6` as possible: WS close/error is the fallback.
