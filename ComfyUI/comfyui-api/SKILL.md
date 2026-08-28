---
name: comfyui-api
description: Connect to a current ComfyUI server, inspect capabilities, submit API-format prompts, monitor execution, retrieve outputs, and control the queue. Use for REST or WebSocket automation and server diagnostics.
---

# ComfyUI server API

Use the server's discovered routes as the final authority. Default local base URL is http://127.0.0.1:8188.

## Core flow

1. GET /system_stats to confirm the server and inspect runtime information.
2. GET /object_info to discover installed node class types and schemas.
3. Obtain an API-format prompt from the UI's API export or build one from /object_info.
4. POST /prompt with prompt and a unique client_id.
5. Connect to /ws?clientId=CLIENT_ID and monitor the matching prompt_id.
6. When execution completes, GET /history/PROMPT_ID.
7. Retrieve output files with /view using the returned filename, subfolder and type.

Example queue body:

    {
      "prompt": {
        "3": {
          "class_type": "KSampler",
          "inputs": {}
        }
      },
      "client_id": "a-unique-client-id"
    }

The abbreviated example is not executable. Supply every required input and valid connection from /object_info.

A successful POST /prompt normally returns a prompt_id plus queue/error information. Treat node_errors as a failed validation even if the HTTP request succeeded.

## Formats

UI workflow JSON and API prompt JSON are different:

- UI workflow format stores visual graph state, links, groups and layout. Current schema documentation is version 1.0.
- API prompt format is an object keyed by node IDs. Each entry has class_type and inputs.

Do not submit UI workflow JSON directly to /prompt. Use the UI's API export or a verified conversion path.

## Useful routes

Current core routes include /prompt, /ws, /history, /history/{prompt_id}, /view, /object_info, /queue, /interrupt, /system_stats and upload/model/userdata routes. Exact methods and parameters are documented at:

https://docs.comfy.org/development/comfyui-server/comms_routes

## Safety

Bind remote servers deliberately, use authentication or a trusted network boundary, and never expose an unauthenticated ComfyUI instance directly to the internet. Validate upload names and do not assume server-returned paths are safe local paths.

## Completion check

Confirm server reachability, prompt validation, prompt_id correlation, terminal WebSocket status, history contents, output download and timeout/cancellation behavior.
