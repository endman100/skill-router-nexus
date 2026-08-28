---
name: comfyui-python-ws-client
description: Implement reliable Python clients for the current ComfyUI HTTP and WebSocket APIs, including prompt correlation, progress, previews, terminal events, timeouts, reconnects, and output retrieval.
---

# Python WebSocket client

Use HTTP to queue and retrieve durable results. Use WebSocket for live execution events.

## Connection sequence

1. Generate a unique client_id.
2. Connect to ws://HOST:PORT/ws?clientId=CLIENT_ID.
3. POST the API-format prompt to /prompt with the same client_id.
4. Read WebSocket frames until the returned prompt_id reaches a terminal state.
5. GET /history/PROMPT_ID and download outputs through /view.

Register the WebSocket before queueing when missing very early events matters.

## Event handling

Text frames contain JSON messages. Handle current message types defensively rather than assuming a fixed exhaustive list. Useful events include queue status, execution start, cache hits, executing nodes, progress, executed results, success and execution errors.

Filter every execution event by prompt_id when the message includes one. An executing event with a null node may indicate graph execution ended in older/current variants, but prefer explicit success/error messages and verify history.

Binary frames can carry preview data. Parse only when previews are required and follow the official binary framing for the server version. Never decode arbitrary binary frames as UTF-8.

## Reliability

- Set connect, receive and overall execution deadlines.
- Close sockets explicitly in finally or a context manager.
- Do not rely on __del__ for cleanup.
- On disconnect, query /history and /queue before deciding whether to reconnect or resubmit.
- Never resubmit automatically unless the operation is known to be idempotent.
- Surface prompt validation errors, execution errors and timeout as different failures.
- Use TLS and authentication when a reverse proxy exposes the service remotely.

## Minimal structure

    client_id = str(uuid.uuid4())
    ws = websocket.create_connection(f'ws://{host}/ws?clientId={client_id}', timeout=10)
    try:
        queued = requests.post(
            f'http://{host}/prompt',
            json={'prompt': prompt, 'client_id': client_id},
            timeout=30,
        ).json()
        prompt_id = queued['prompt_id']
        # Read frames, correlate prompt_id, stop on success/error/deadline.
        history = requests.get(
            f'http://{host}/history/{prompt_id}',
            timeout=30,
        ).json()
    finally:
        ws.close()

Add status checks and error handling before production use.

## Sources

- https://docs.comfy.org/development/comfyui-server/api-examples
- https://docs.comfy.org/development/comfyui-server/comms_messages
- https://docs.comfy.org/development/comfyui-server/comms_routes
