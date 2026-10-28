#!/usr/bin/env python3
"""Codex ChatGPT Responses-over-WebSocket single-turn client (skill script)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import websockets
from uuid6 import uuid7

CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
WS_URL = "wss://chatgpt.com/backend-api/codex/responses"
ORIGINATOR = "codex_clone"  # mark as our clone; use codex_exec to match CLI byte-for-byte
CLI_VERSION = "0.163.0"
OPENAI_BETA = "responses_websockets=2026-02-06"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def load_auth() -> tuple[str, str]:
    auth = load_json(CODEX_HOME / "auth.json")
    tokens = auth["tokens"]
    return tokens["access_token"], tokens["account_id"]


def load_config() -> dict[str, Any]:
    # minimal TOML parse for keys we need
    text = (CODEX_HOME / "config.toml").read_text()
    out: dict[str, Any] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("["):
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        k, v = k.strip(), v.strip().strip('"')
        out[k] = v
    return out


def load_model(slug: str) -> dict[str, Any]:
    cache = load_json(CODEX_HOME / "models_cache.json")
    for m in cache["models"]:
        if m["slug"] == slug:
            return m
    raise SystemExit(f"model {slug} not in models_cache.json — run codex once first")


def installation_id() -> str:
    return (CODEX_HOME / "installation_id").read_text().strip()


def uuid_v5_oid(name: bytes) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_OID, name.decode() if isinstance(name, bytes) else name)


def item_id(prefix: str, namespace: uuid.UUID, material: bytes | str) -> str:
    if isinstance(material, str):
        material = material.encode()
    u = uuid.uuid5(namespace, material.decode("latin1") if False else hashlib.sha1(material).hexdigest())
    # Match Codex: Uuid::new_v5(&prefix_namespace, bytes) — use raw bytes via uuid5 name
    u = uuid.uuid5(namespace, material.decode("utf-8", errors="surrogateescape") if isinstance(material, (bytes, bytearray)) else material)
    # uuid.uuid5 expects str; for bytes use decode
    return f"{prefix}_{u}"


def item_id_bytes(prefix: str, namespace: uuid.UUID, material: bytes) -> str:
    # Python uuid5 takes str; Codex hashes raw bytes. Emulate with latin1 roundtrip of bytes.
    u = uuid.uuid5(namespace, material.decode("latin1"))
    return f"{prefix}_{u}"


def new_turn_id() -> str:
    return str(uuid7())


def user_agent() -> str:
    system = platform.system()
    release = platform.release()
    machine = platform.machine()
    return f"codex_exec/{CLI_VERSION} ({system} {release}; {machine}) dumb (codex_exec; {CLI_VERSION})"


def build_permissions(sandbox_mode: str = "read-only") -> str:
    return (
        "<permissions instructions>\n"
        "Filesystem sandboxing defines which files can be read or written. "
        f"`sandbox_mode` is `{sandbox_mode}`: The sandbox only permits reading files. "
        "Network access is restricted.\n"
        "Approval policy is currently never. Do not provide the `sandbox_permissions` "
        "for any reason, commands will be rejected.\n"
        "</permissions instructions>"
    )


def build_environment(cwd: Path) -> str:
    return (
        "<environment_context>\n"
        f"  <cwd>{cwd}</cwd>\n"
        "  <shell>bash</shell>\n"
        f"  <current_date>{date.today().isoformat()}</current_date>\n"
        "  <timezone>Asia/Taipei</timezone>\n"
        f"  <filesystem><workspace_roots><root>{cwd}</root></workspace_roots>"
        '<permission_profile type="managed"><file_system type="restricted">'
        '<entry access="read"><special>:root</special></entry>'
        "</file_system></permission_profile></filesystem>\n"
        "</environment_context>"
    )


def build_skills_block() -> str:
    roots = []
    skills = []
    sys_root = CODEX_HOME / "skills" / ".system"
    if sys_root.is_dir():
        roots.append(("r0", str(sys_root)))
        for child in sorted(sys_root.iterdir()):
            skill_md = child / "SKILL.md"
            if skill_md.is_file():
                # first line description heuristic
                name = child.name
                desc = name
                for line in skill_md.read_text(errors="ignore").splitlines()[:20]:
                    if line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip().strip('"')
                        break
                skills.append(f"- {name}: {desc}")
    root_lines = "\n".join(f"- `{a}` = `{p}`" for a, p in roots) or "- (none)"
    skill_lines = "\n".join(skills) or "- (none)"
    return (
        "<skills_instructions>\n## Skills\n"
        "A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. "
        "Below is the list of skills that can be used.\n"
        "### Skill roots\n"
        f"{root_lines}\n"
        "### Available skills\n"
        f"{skill_lines}\n"
        "</skills_instructions>"
    )


def wrap_collab(text: str) -> str:
    return f"<collaboration_mode>{text}</collaboration_mode>"


def wrap_multi_agent_role(text: str) -> str:
    return f"<multi_agent_role>{text}</multi_agent_role>"


def multi_agent_mode_off() -> str:
    return (
        "<multi_agent_mode>Any earlier instruction enabling proactive multi-agent delegation "
        "no longer applies. Do not spawn sub-agents unless the user or applicable AGENTS.md/skill "
        "instructions explicitly ask for sub-agents, delegation, or parallel agent work."
        "</multi_agent_mode>"
    )


def recommended_plugins_from_capture() -> str:
    # Stable curated list observed in live capture; optional to refresh via plugins API.
    return (
        "<recommended_plugins>\n"
        "Here is a list of plugins that are available but not installed.\n\n"
        "- Dropbox (app-69b31dc2110c8191b8b47dc98fe5a052@openai-curated-remote)\n"
        "- Box (box@openai-curated-remote)\n"
        "- Codex Security (codex-security@openai-curated-remote)\n"
        "- Figma (figma@openai-curated-remote)\n"
        "- Linear (linear@openai-curated-remote)\n"
        "- Outlook Calendar (outlook-calendar@openai-curated-remote)\n"
        "- Outlook Email (outlook-email@openai-curated-remote)\n"
        "- SharePoint (sharepoint@openai-curated-remote)\n"
        "- Teams (teams@openai-curated-remote)\n"
        "</recommended_plugins>"
    )


def msg(
    *,
    role: str,
    text_parts: list[str],
    item_id: str,
    kinds: list[str],
    turn_id: str | None = None,
    create_time: float | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {"content_item_kinds": kinds}
    if turn_id is not None:
        meta["turn_id"] = turn_id
    if create_time is not None:
        meta["create_time"] = create_time
    return {
        "type": "message",
        "id": item_id,
        "role": role,
        "content": [{"type": "input_text", "text": t} for t in text_parts],
        "internal_chat_message_metadata_passthrough": meta,
    }


def turn_metadata(
    *,
    inst: str,
    session_id: str,
    turn_id: str,
    window_id: str,
    context_window_id: str,
    request_kind: str,
    model: str,
    effort: str,
    sandbox_mode: str,
    turn_started_at_unix_ms: int | None = None,
) -> str:
    payload = {
        "installation_id": inst,
        "session_id": session_id,
        "thread_id": session_id,
        "agent_name": "/root",
        "turn_id": turn_id,
        "window_id": window_id,
        "window_number": 0,
        "context_window_id": context_window_id,
        "request_kind": request_kind,
        "history_initialization": "new",
        "thread_source": "user",
        "sandbox": "seccomp",
        "sandbox_mode": sandbox_mode,
        "auto_review_enabled": False,
        "node_repl_auto_review_required": True,
        "node_repl_disabled": False,
        "analytics_enabled": True,
        "model": model,
        "reasoning_effort": effort,
    }
    if request_kind == "turn":
        payload["root_turn_id"] = turn_id
        payload["turn_trigger"] = "exec"
        payload["turn_started_at_unix_ms"] = turn_started_at_unix_ms or int(time.time() * 1000)
    return json.dumps(payload, separators=(",", ":"))


def client_metadata(
    *,
    inst: str,
    session_id: str,
    turn_id: str,
    window_id: str,
    context_window_id: str,
    request_kind: str,
    model: str,
    effort: str,
    sandbox_mode: str,
    turn_started_at_unix_ms: int | None = None,
) -> dict[str, str]:
    md = {
        "x-codex-turn-metadata": turn_metadata(
            inst=inst,
            session_id=session_id,
            turn_id=turn_id,
            window_id=window_id,
            context_window_id=context_window_id,
            request_kind=request_kind,
            model=model,
            effort=effort,
            sandbox_mode=sandbox_mode,
            turn_started_at_unix_ms=turn_started_at_unix_ms,
        ),
        "guardian_credits_requested": "true",
        "thread_id": session_id,
        "session_id": session_id,
        "x-codex-ws-stream-request-start-ms": str(int(time.time() * 1000)),
        "mcp_attribution": json.dumps({"status": "none"}),
        "turn_id": turn_id,
        "x-codex-installation-id": inst,
        "ws_request_header_x_openai_internal_codex_responses_lite": "true",
        "x-codex-window-id": window_id,
    }
    if request_kind == "turn":
        md["root_turn_id"] = turn_id
    return md


# Embedded Responses Lite tool schemas captured from Codex 0.163.0 wire (gpt-6.1-sol).
# Re-capture with mitm when upgrading CLI; replace this constant.
_EMBEDDED_TOOLS_JSON = '[{"type":"namespace","name":"functions","description":"","tools":[{"type":"custom","name":"exec","description":"Run JavaScript code to orchestrate/compose tool calls\\n- Evaluates the provided JavaScript code in a fresh V8 isolate as an async module.\\n- All nested tools are available on the global `tools` object, for example `await tools.exec_command(...)`. Tool names are exposed as normalized JavaScript identifiers, for example `await tools.mcp__ologs__get_profile(...)`.\\n- Nested tool methods take either a string or an object as their input argument.\\n- Nested tools return either an object or a string, based on the description.\\n- Runs raw JavaScript -- no Node, no file system, no network access, no console.\\n- Accepts raw JavaScript source text, not JSON, quoted strings, or markdown code fences.\\n- You may optionally start the tool input with a first-line pragma like `// @exec: {\\"yield_time_ms\\": 10000, \\"max_output_tokens\\": 1000}`.\\n- `yield_time_ms` asks `exec` to yield early if the script is still running. Defaults to 30000 ms.\\n- `max_output_tokens` sets the token budget for direct `exec` results. Defaults to 10000 tokens.\\n- When the JS code is fully evaluated, the isolate\'s lifetime ends and unawaited promises are silently discarded.\\n\\n- Global helpers:\\n- `exit()`: Immediately ends the current script successfully (like an early return from the top level).\\n- `text(value: string | number | boolean | undefined | null)`: Appends a text item. Non-string values are stringified with `JSON.stringify(...)` when possible.\\n- `image(imageUrlOrItem: string | { image_url: string; detail?: \\"auto\\" | \\"low\\" | \\"high\\" | \\"original\\" | null } | ImageContent, detail?: \\"auto\\" | \\"low\\" | \\"high\\" | \\"original\\" | null)`: Appends an image item. `image_url` should be a base64-encoded `data:` URL. To forward an MCP tool image, pass an individual `ImageContent` block from `result.content`, for example `image(result.content[0])`. MCP image blocks may request detail with `_meta: { \\"codex/imageDetail\\": \\"original\\" }`. When provided, the second `detail` argument overrides any detail embedded in the first argument.\\n- `audio(audioUrlOrItem: string | { audio_url: string } | AudioContent)`: Appends an audio item. `audio_url` should be a base64-encoded `data:` URL. To forward an MCP tool audio block, pass an individual `AudioContent` block from `result.content`, for example `audio(result.content[0])`.\\n- `generatedImage(result: { image_url: string; output_hint?: string })`: Appends an image-generation result and its optional output hint. HTTP(S) URLs are not supported.\\n- `store(key: string, value: any)`: stores a serializable value under a string key for later `exec` calls in the same session.\\n- `load(key: string)`: returns the stored value for a string key, or `undefined` if it is missing.\\n- `notify(value: string | number | boolean | undefined | null)`: immediately injects an extra `custom_tool_call_output` for the current `exec` call. Values are stringified like `text(...)`.\\n- `setTimeout(callback: () => void, delayMs?: number)`: schedules a callback to run later and returns a timeout id. Pending timeouts do not keep `exec` alive by themselves; await an explicit promise if you need to wait for one.\\n- `clearTimeout(timeoutId?: number)`: cancels a timeout created by `setTimeout`.\\n- `ALL_TOOLS`: metadata for the enabled nested tools as `{ name, description }` entries.\\n- `yield_control()`: yields the accumulated output to the model immediately while the script keeps running.\\n\\nSome deferred nested tools may be omitted from this description. They are still available on the global `tools` object and listed in `ALL_TOOLS`.\\nTo find one, filter `ALL_TOOLS` by `name` and `description`.\\n\\nTool availability can change between calls.\\n\\nShared MCP Types:\\n```ts\\ntype Role = \\"user\\" | \\"assistant\\";\\ntype MetaObject = Record<string, unknown>;\\ntype Annotations = {\\n  audience?: Role[];\\n  priority?: number;\\n  lastModified?: string;\\n};\\ntype Icon = {\\n  src: string;\\n  mimeType?: string;\\n  sizes?: string[];\\n  theme?: \\"light\\" | \\"dark\\";\\n};\\ntype TextResourceContents = {\\n  uri: string;\\n  mimeType?: string;\\n  _meta?: MetaObject;\\n  text: string;\\n};\\ntype BlobResourceContents = {\\n  uri: string;\\n  mimeType?: string;\\n  _meta?: MetaObject;\\n  blob: string;\\n};\\ntype TextContent = {\\n  type: \\"text\\";\\n  text: string;\\n  annotations?: Annotations;\\n  _meta?: MetaObject;\\n};\\ntype ImageContent = {\\n  type: \\"image\\";\\n  data: string;\\n  mimeType: string;\\n  annotations?: Annotations;\\n  _meta?: MetaObject;\\n};\\ntype AudioContent = {\\n  type: \\"audio\\";\\n  data: string;\\n  mimeType: string;\\n  annotations?: Annotations;\\n  _meta?: MetaObject;\\n};\\ntype ResourceLink = {\\n  icons?: Icon[];\\n  name: string;\\n  title?: string;\\n  uri: string;\\n  description?: string;\\n  mimeType?: string;\\n  annotations?: Annotations;\\n  size?: number;\\n  _meta?: MetaObject;\\n  type: \\"resource_link\\";\\n};\\ntype EmbeddedResource = {\\n  type: \\"resource\\";\\n  resource: TextResourceContents | BlobResourceContents;\\n  annotations?: Annotations;\\n  _meta?: MetaObject;\\n};\\ntype ContentBlock =\\n  | TextContent\\n  | ImageContent\\n  | AudioContent\\n  | ResourceLink\\n  | EmbeddedResource;\\ntype CallToolResult<TStructured = { [key: string]: unknown }> = {\\n  _meta?: MetaObject;\\n  content: ContentBlock[];\\n  isError?: boolean;\\n  structuredContent?: TStructured;\\n  [key: string]: unknown;\\n};\\n```\\n\\n### `apply_patch`\\nThe `apply_patch` tool can be used to edit files. This is a FREEFORM tool, so do not wrap the patch in JSON.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { apply_patch(input: string): Promise<unknown>; };\\n```\\n\\n### `create_goal`\\nCreate a goal only when explicitly requested by the user or system/developer instructions; do not infer goals from ordinary tasks.\\nSet token_budget only when an explicit token budget is requested. Fails if an unfinished goal exists; use update_goal only for status.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { create_goal(args: {\\n  // Required. The concrete objective to start pursuing. This starts a new active goal when no goal exists or replaces the current goal when it is complete.\\n  objective: string;\\n  // Positive token budget for the new goal. Omit unless explicitly requested.\\n  token_budget?: number;\\n}): Promise<unknown>; };\\n```\\n\\n### `exec_command`\\nRuns a command in a PTY, returning output or a session ID for ongoing interaction.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { exec_command(args: {\\n  // Shell command to execute.\\n  cmd: string;\\n  // User-facing approval question for `require_escalated`; omit otherwise.\\n  justification?: string;\\n  // True runs the shell with -l/-i semantics; false disables them. Defaults to true.\\n  login?: boolean;\\n  // Output token budget. Defaults to 10000 tokens; larger requests may be capped by policy.\\n  max_output_tokens?: number;\\n  // Reusable approval prefix for `cmd`, only with `sandbox_permissions: \\"require_escalated\\"`; for example [\\"git\\", \\"pull\\"].\\n  prefix_rule?: Array<string>;\\n  // Per-command sandbox override. Defaults to `use_default`; use `require_escalated` for unsandboxed execution.\\n  sandbox_permissions?: \\"use_default\\" | \\"require_escalated\\";\\n  // Shell binary to launch. Defaults to the user\'s default shell.\\n  shell?: string;\\n  // True allocates a PTY for the command; false or omitted uses plain pipes.\\n  tty?: boolean;\\n  // Working directory for the command. Defaults to the turn cwd.\\n  workdir?: string;\\n  // Wait before yielding output. Defaults to 10000 ms; effective range is 250-30000 ms.\\n  yield_time_ms?: number;\\n}): Promise<{\\n  // Chunk identifier included when the response reports one.\\n  chunk_id?: string;\\n  // Process exit code when the command finished during this call.\\n  exit_code?: number;\\n  // Approximate token count before output truncation.\\n  original_token_count?: number;\\n  // Command output text, possibly truncated.\\n  output: string;\\n  // Session identifier to pass to write_stdin when the process is still running.\\n  session_id?: number;\\n  // Elapsed wall time spent waiting for output in seconds.\\n  wall_time_seconds: number;\\n}>; };\\n```\\n\\n### `get_goal`\\nGet the current goal for this thread, including status, budgets, token and elapsed-time usage, and remaining token budget.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { get_goal(args: {}): Promise<unknown>; };\\n```\\n\\n### `list_mcp_resource_templates`\\nLists resource templates provided by MCP servers. Parameterized resource templates allow servers to share data that takes parameters and provides context to language models, such as files, database schemas, or application-specific information. Prefer resource templates over web search when possible.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { list_mcp_resource_templates(args: {\\n  // Opaque cursor from a previous list_mcp_resource_templates call; omit for the first page.\\n  cursor?: string;\\n  // MCP server name. Omit to list resource templates from every configured server.\\n  server?: string;\\n}): Promise<unknown>; };\\n```\\n\\n### `list_mcp_resources`\\nLists resources provided by MCP servers. Resources allow servers to share data that provides context to language models, such as files, database schemas, or application-specific information. Prefer resources over web search when possible.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { list_mcp_resources(args: {\\n  // Opaque cursor from a previous list_mcp_resources call; omit for the first page.\\n  cursor?: string;\\n  // MCP server name. Omit to list resources from every configured server.\\n  server?: string;\\n}): Promise<unknown>; };\\n```\\n\\n### `read_mcp_resource`\\nRead a specific resource from an MCP server given the server name and resource URI.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { read_mcp_resource(args: {\\n  // MCP server name exactly as configured. Must match the \'server\' field returned by list_mcp_resources.\\n  server: string;\\n  // Resource URI to read. Must be one of the URIs returned by list_mcp_resources.\\n  uri: string;\\n}): Promise<unknown>; };\\n```\\n\\n### `request_plugin_install`\\n# Suggest a recommended plugin installation\\n\\nUse this tool only when all of the following are true:\\n- The user explicitly asks to use a specific plugin that is not already available in the current context or active `tools` list.\\n- Tool search has already been exhausted and did not find or make the requested tool callable.\\n- The plugin is listed in `<recommended_plugins>`.\\n\\nDo not use it for adjacent capabilities, broad recommendations, or plugins that merely seem useful. Briefly explain why the plugin can help with the current request in `suggest_reason`.\\n\\nIMPORTANT: DO NOT call this tool in parallel with other tools.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { request_plugin_install(args: {\\n  // The parenthesized plugin ID from the `<recommended_plugins>` list.\\n  plugin_id: string;\\n  // Concise one-line user-facing reason why this plugin can help with the current request.\\n  suggest_reason: string;\\n}): Promise<unknown>; };\\n```\\n\\n### `update_goal`\\nUpdate the existing goal.\\nSet status to `paused` only at the user\'s explicit request to pause this goal, never on your own initiative. Ask if unclear; a later resume revokes that request. Report the returned status and stop goal work. Budget limits take precedence over pausing.\\nSet status to `complete` only when the objective has actually been achieved and no required work remains.\\nSet status to `blocked` only when the same blocking condition has repeated for at least three consecutive goal turns, counting the original/user-triggered turn and any automatic continuations, and the agent cannot make meaningful progress without user input or an external-state change.\\nIf the user resumes a goal that was previously marked `blocked`, treat the resumed run as a fresh blocked audit. If the same blocking condition then repeats for at least three consecutive resumed goal turns, set status to `blocked` again.\\nOnce the blocked threshold is satisfied, do not keep reporting that you are still blocked while leaving the goal active; set status to `blocked`.\\nDo not use `blocked` merely because the work is hard, slow, uncertain, incomplete, or would benefit from clarification.\\nDo not mark a goal complete merely because its budget is nearly exhausted or because you are stopping work.\\nYou cannot use this tool to resume, budget-limit, or usage-limit a goal; those status changes are controlled by the user or system.\\nWhen marking a budgeted goal achieved with status `complete`, report the final token usage from the tool result to the user.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { update_goal(args: {\\n  // Required. `paused` requires an explicit user request. Set to `complete` only when the objective is achieved and no required work remains. Set to `blocked` only after the same blocking condition has recurred for at least three consecutive goal turns and the agent is at an impasse. After a previously blocked goal is resumed, the resumed run starts a fresh blocked audit.\\n  status: \\"complete\\" | \\"blocked\\" | \\"paused\\";\\n}): Promise<unknown>; };\\n```\\n\\n### `view_image`\\nView a local image file from the filesystem when visual inspection is needed. Use this for images already available on disk.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { view_image(args: {\\n  // Image detail level. Defaults to `high`; use `original` to preserve exact resolution.\\n  detail?: \\"high\\" | \\"original\\";\\n  // Local filesystem path to an image file.\\n  path: string;\\n}): Promise<{\\n  // Image detail hint returned by view_image. Returns `high` for default resized behavior or `original` when original resolution is preserved.\\n  detail: \\"high\\" | \\"original\\";\\n  // Data URL for the loaded image.\\n  image_url: string;\\n}>; };\\n```\\n\\n### `write_stdin`\\nWrites characters to an existing unified exec session and returns recent output.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { write_stdin(args: {\\n  // Bytes to write to stdin. Defaults to empty, which polls without writing.\\n  chars?: string;\\n  // Output token budget. Defaults to 10000 tokens; larger requests may be capped by policy.\\n  max_output_tokens?: number;\\n  // Identifier of the running unified exec session.\\n  session_id: number;\\n  // Wait before yielding output. Non-empty writes default to 250 ms and cap at 30000 ms; empty polls wait 5000-300000 ms by default.\\n  yield_time_ms?: number;\\n}): Promise<{\\n  // Chunk identifier included when the response reports one.\\n  chunk_id?: string;\\n  // Process exit code when the command finished during this call.\\n  exit_code?: number;\\n  // Approximate token count before output truncation.\\n  original_token_count?: number;\\n  // Command output text, possibly truncated.\\n  output: string;\\n  // Session identifier to pass to write_stdin when the process is still running.\\n  session_id?: number;\\n  // Elapsed wall time spent waiting for output in seconds.\\n  wall_time_seconds: number;\\n}>; };\\n```\\n\\n## clock\\nTools for reading and waiting on time.\\n\\n### `clock__curr_time`\\nReturn the current time in UTC.\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { clock__curr_time(args: {}): Promise<{\\n  // Current UTC time formatted as YYYY-MM-DD HH:MM:SS UTC.\\n  current_time: string;\\n}>; };\\n```\\n\\n## image_gen\\nTools in the image_gen namespace.\\n\\n### `image_gen__imagegen`\\nThe `image_gen.imagegen` tool enables image generation from descriptions and editing of existing images based on specific instructions. Use it when:\\n\\n- The user requests an image based on a scene description, such as a diagram, portrait, comic, meme, or any other visual.\\n- The user wants to modify an attached or previously generated image with specific changes, including adding or removing elements, altering colors, improving quality/resolution, or transforming the style (e.g., cartoon, oil painting).\\n\\nGuidelines:\\n- imagegen needs a few minutes to finish. In code-mode, use the first-line @exec directive to give the initial call 120 seconds and the same yield for any waits that follow. Once it finishes, return the image with generatedImage(result).\\n- Avoid printing the full result or its base64 image data with `text()` or `notify()`; print only small metadata when needed.\\n- Set `transparent_background` to true when the request calls for a transparent background, including background removal or a cutout; set it to false otherwise. For edits, preserve existing transparency unless the user asks to change it.\\n- Omit both `referenced_image_paths` and `num_last_images_to_include` when generating a brand new image.\\n- For edits, use `referenced_image_paths` when every target image has a local file path.\\n- If you have not seen a local image yet, use `view_image` to inspect it before editing.\\n- Use `num_last_images_to_include` only when at least one target image has no local file path.\\n- Set `num_last_images_to_include` to the smallest number of recent conversation images that includes every target image, up to 5.\\n- Never provide both `referenced_image_paths` and `num_last_images_to_include`.\\n- If neither mechanism can include every target image, ask the user to attach the missing images again.\\n- Directly generate the image without reconfirmation or clarification unless required images must be attached again.\\n- Always use this tool for image editing unless the user explicitly requests otherwise. Do not use the `python` tool for image editing unless specifically instructed.\\n\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { image_gen__imagegen(args: {\\n  num_last_images_to_include?: number | null;\\n  prompt: string;\\n  referenced_image_paths?: Array<string> | null;\\n  // Whether the output should have a transparent background. Defaults to false.\\n  transparent_background?: boolean;\\n}): Promise<unknown>; };\\n```\\n\\n## web\\nTools in the web namespace.\\n\\n### `web__run`\\nTool for accessing the internet.\\n\\n\\n---\\n\\n## Examples of different commands available in this tool\\n\\nExamples of different commands available in this tool:\\n* `search_query`: {\\"search_query\\": [{\\"q\\": \\"What is the capital of France?\\"}, {\\"q\\": \\"What is the capital of belgium?\\"}]}. Searches the internet for a given query (and optionally with a domain or recency filter)\\n* `image_query`: {\\"image_query\\":[{\\"q\\": \\"waterfalls\\"}]}.\\n* `open`: {\\"open\\": [{\\"ref_id\\": \\"turn0search0\\"}, {\\"ref_id\\": \\"https://www.openai.com\\", \\"lineno\\": 120}]}\\n* `click`: {\\"click\\": [{\\"ref_id\\": \\"turn0fetch3\\", \\"id\\": 17}]}\\n* `find`: {\\"find\\": [{\\"ref_id\\": \\"turn0fetch3\\", \\"pattern\\": \\"Annie Case\\"}]}\\n* `screenshot`: {\\"screenshot\\": [{\\"ref_id\\": \\"turn1view0\\", \\"pageno\\": 0}, {\\"ref_id\\": \\"turn1view0\\", \\"pageno\\": 3}]}\\n* `finance`: {\\"finance\\":[{\\"ticker\\":\\"AMD\\",\\"type\\":\\"equity\\",\\"market\\":\\"USA\\"}]}, {\\"finance\\":[{\\"ticker\\":\\"BTC\\",\\"type\\":\\"crypto\\",\\"market\\":\\"\\"}]}\\n* `weather`: {\\"weather\\":[{\\"location\\":\\"San Francisco, CA\\"}]}\\n* `sports`: {\\"sports\\":[{\\"fn\\":\\"standings\\",\\"league\\":\\"nfl\\"}, {\\"fn\\":\\"schedule\\",\\"league\\":\\"nba\\",\\"team\\":\\"GSW\\",\\"date_from\\":\\"2025-02-24\\"}]}\\n* `time`: {\\"time\\":[{\\"utc_offset\\":\\"+03:00\\"}]}\\n\\n---\\n\\n## Usage hints\\nTo use this tool efficiently:\\n* Use multiple commands and queries in one call to get more results faster; e.g. {\\"search_query\\": [{\\"q\\": \\"bitcoin news\\"}], \\"finance\\":[{\\"ticker\\":\\"BTC\\",\\"type\\":\\"crypto\\",\\"market\\":\\"\\"}], \\"find\\": [{\\"ref_id\\": \\"turn0search0\\", \\"pattern\\": \\"Annie Case\\"}, {\\"ref_id\\": \\"turn0search1\\", \\"pattern\\": \\"John Smith\\"}]}\\n* Use \\"response_length\\" to control the number of results returned by this tool, omit it if you intend to pass \\"short\\" in\\n* Only write required parameters; do not write empty lists or nulls where they could be omitted.\\n* `search_query` must have length at most 4 in each call. If it has length > 3, response_length must be medium or long\\n* If you find yourself in a situation where you accidentally call the `web.run` tool, it\'s best just to send an empty query: {\\"search_query\\": [{\\"q\\": \\"\\"}]}.\\n\\n---\\n\\n## Decision boundary\\n\\nIf the user makes an explicit request to search the internet, find latest information, look up, etc (or to not do so), you must obey their request.\\nWhen you make an assumption, always consider whether it is temporally stable; i.e. whether there\'s even a small (>10%) chance it has changed. If it is unstable, you must verify with browsing the internet for verification.\\n\\n<situations_where_you_must_browse_the_internet>\\nBelow is a list of scenarios where browsing the internet MUST be used. PAY CLOSE ATTENTION: you MUST browse the internet in these cases. If you\'re unsure or on the fence, you MUST bias towards browsing the internet.\\n- The information could have changed recently: for example news; prices; laws; schedules; product specs; sports scores; economic indicators; political/public/company figures (e.g. the question relates to \'the president of country A\' or \'the CEO of company B\', which might change over time); rules; regulations; standards; software libraries that could be updated; exchange rates; recommendations (i.e., recommendations about various topics or things might be informed by what currently exists / is popular / is safe / is unsafe / is in the zeitgeist / etc.); and many many many more categories -- again, if you\'re on the fence, you MUST browse the internet!\\n  - For news queries, prioritize more recent events, ensuring you compare publish dates and the date that the event happened.\\n- The user is seeking recommendations that could lead them to spend substantial time or money -- researching products, restaurants, travel plans, etc.\\n- The user wants (or would benefit from) direct quotes, links, or precise source attribution.\\n- A specific page, paper, dataset, PDF, or site is referenced and you haven\'t been given its contents.\\n- You\'re unsure about a fact, the topic is niche or emerging, or you suspect there\'s at least a 10% chance you will incorrectly recall it\\n- High-stakes accuracy matters (medical, legal, financial guidance). For these you generally should search by default because this information is highly temporally unstable\\n- The user explicitly says to search, browse, verify, or look it up.\\n</situations_where_you_must_browse_the_internet>\\n\\n---\\n\\n## Citations\\n\\nResults from `web.run` include internal reference IDs such as `turn2search5`. Use\\nthose reference IDs only in calls to `web.run`; do not expose them in the final\\nresponse.\\n\\nCite sources in the final response using Markdown links:\\n\\n- Cite a single source as `[descriptive source title](https://example.com/page)`.\\n- Cite multiple sources with separate Markdown links, for example\\n  `[first source](https://example.com/one), [second source](https://example.com/two)`.\\n- Link directly to the page that supports the claim. Do not link to search result\\n  pages or use bare URLs.\\n\\nFormatting of citations:\\n\\n- Place each citation as near as possible to the claim it supports, normally at\\n  the end of the sentence or paragraph and after punctuation.\\n- Do not place citations inside code fences.\\n- Do not put citations on a line by themselves or collect all citations at the\\n  end of the response.\\n\\nIf you browse the internet, cite statements supported by web sources. Each cited\\nsource must directly support the associated claim. Prefer primary and\\nauthoritative sources, and use sources from different domains when the response\\nbenefits from multiple perspectives.\\n\\n---\\n\\n## Special cases\\nIf these conflict with any other instructions, these should take precedence.\\n\\n<special_cases>\\n- When the user asks for information about how to use OpenAI products, (ChatGPT, the OpenAI API, etc.), you should check the code in local env and only browse as fallback, when you browse restrict your sources to official OpenAI websites using the domains filter, unless otherwise requested.\\n- When using search to answer technical questions, you must only rely on primary sources (research papers, official documentation, etc.)\\n- Clearly indicate when you are making an inference from sources.\\n</special_cases>\\n\\n---\\n\\n## Word limits\\nResponses may not excessively quote or draw on a specific source. There are several limits here:\\n- **Limit on verbatim quotes:**\\n  - You may not quote more than 25 words verbatim from any single non-lyrical source, unless the source is reddit.\\n  - For song lyrics, verbatim quotes must be limited to at most 10 words.\\n  - Long quotes from reddit are allowed, as long as you indicate that those are direct quotes via a markdown blockquote starting with \\">\\", copy verbatim, and link the source.\\n- **Word limits:**\\n  - Each webpage source in the sources has a word limit label formatted like \\"[wordlim N]\\", in which N is the maximum number of words in the whole response that are attributed to that source. If omitted, the word limit is 200 words.\\n  - Non-contiguous words derived from a given source must be counted to the word limit.\\n  - The summarization limit N is a maximum for each source.\\n  - When using multiple sources, their summarization limits add together. However, each article used must be relevant to the response.\\n- **Copyright compliance:**\\n  - You must avoid providing full articles, long verbatim passages, or extensive direct quotes due to copyright concerns.\\n  - If the user asked for a verbatim quote, the response should provide a short compliant excerpt and then answer with paraphrases and summaries.\\n  - Again, this limit does not apply to reddit content, as long as it\'s appropriately indicated that those are direct quotes and you link to the source.\\n\\n\\nexec tool declaration:\\n```ts\\ndeclare const tools: { web__run(args: {\\n  // Open links from previously opened pages.\\n  click?: Array<{\\n  // Numbered link id to open.\\n  id: number;\\n  // Reference id containing the numbered link.\\n  ref_id: string;\\n}>;\\n  // Look up prices for the given stock symbols.\\n  finance?: Array<{\\n  // ISO 3166-1 alpha-3 country code, \\"OTC\\", or \\"\\" for cryptocurrency.\\n  market?: string;\\n  // Ticker symbol to look up.\\n  ticker: string;\\n  // Asset type to look up.\\n  type: \\"equity\\" | \\"fund\\" | \\"crypto\\" | \\"index\\";\\n}>;\\n  // Find text patterns in pages.\\n  find?: Array<{\\n  // Text pattern to find.\\n  pattern: string;\\n  // Reference id or URL to search within.\\n  ref_id: string;\\n}>;\\n  // Query the image search engine for a given list of queries.\\n  image_query?: Array<{\\n  // Whether to filter by a specific list of domains.\\n  domains?: Array<string>;\\n  // Search query.\\n  q: string;\\n  // Whether to filter by recency, as a number of recent days.\\n  recency?: number;\\n}>;\\n  // Open pages by reference id or URL.\\n  open?: Array<{\\n  // Line number to position the page at.\\n  lineno?: number;\\n  // Reference id or URL to open.\\n  ref_id: string;\\n}>;\\n  // Set the length of the response to be returned.\\n  response_length?: \\"short\\" | \\"medium\\" | \\"long\\";\\n  // Take screenshots of PDF pages.\\n  screenshot?: Array<{\\n  // Zero-indexed PDF page number.\\n  pageno: number;\\n  // Reference id or URL to screenshot.\\n  ref_id: string;\\n}>;\\n  // Query the internet search engine for a given list of queries.\\n  search_query?: Array<{\\n  // Whether to filter by a specific list of domains.\\n  domains?: Array<string>;\\n  // Search query.\\n  q: string;\\n  // Whether to filter by recency, as a number of recent days.\\n  recency?: number;\\n}>;\\n  // Look up sports schedules and standings.\\n  sports?: Array<{\\n  // Start date in YYYY-MM-DD format.\\n  date_from?: string;\\n  // End date in YYYY-MM-DD format.\\n  date_to?: string;\\n  // Sports function to call.\\n  fn: \\"schedule\\" | \\"standings\\";\\n  // League to look up.\\n  league: \\"nba\\" | \\"wnba\\" | \\"nfl\\" | \\"nhl\\" | \\"mlb\\" | \\"epl\\" | \\"ncaamb\\" | \\"ncaawb\\" | \\"ipl\\";\\n  // Locale for the lookup.\\n  locale?: string;\\n  // Number of games to return.\\n  num_games?: number;\\n  // Opponent to use with `team` when narrowing the lookup.\\n  opponent?: string;\\n  // Team to look up, using the common 3 or 4 letter alias used in broadcasts.\\n  team?: string;\\n  // Tool name for sports requests.\\n  tool?: \\"sports\\";\\n}>;\\n  // Get time for the given UTC offsets.\\n  time?: Array<{\\n  // UTC offset formatted like \\"+03:00\\".\\n  utc_offset: string;\\n}>;\\n  // Look up weather forecasts.\\n  weather?: Array<{\\n  // Number of days to return. Defaults to 7.\\n  duration?: number;\\n  // Location in \\"Country, Area, City\\" format.\\n  location: string;\\n  // Start date in YYYY-MM-DD format. Defaults to today.\\n  start?: string;\\n}>;\\n}): Promise<unknown>; };\\n```","format":{"type":"grammar","syntax":"lark","definition":"\\nstart: pragma_source | plain_source\\npragma_source: PRAGMA_LINE NEWLINE SOURCE\\nplain_source: SOURCE\\n\\nPRAGMA_LINE: /[ \\\\t]*\\\\/\\\\/ @exec:[^\\\\r\\\\n]*/\\nNEWLINE: /\\\\r?\\\\n/\\nSOURCE: /[\\\\s\\\\S]+/\\n"}},{"type":"function","name":"wait","description":"Waits on a yielded `exec` cell and returns new output or completion.\\n- Use `wait` only after `exec` returns `Script running with cell ID ...`.\\n- `cell_id` identifies the running `exec` cell to resume.\\n- `yield_time_ms` controls how long to wait for more output before yielding again. Defaults to 10000 ms.\\n- `max_tokens` limits how much new output this wait call returns. Defaults to 10000 tokens.\\n- `terminate: true` stops the running cell; false or omitted waits for output.\\n- `wait` returns only the new output since the last yield, or the final completion or termination result for that cell.\\n- If the cell is still running, `wait` may yield again with the same `cell_id`.\\n- If the cell has already finished, `wait` returns the completed result and closes the cell.","strict":false,"parameters":{"type":"object","properties":{"cell_id":{"type":"string","description":"Identifier of the running exec cell."},"max_tokens":{"type":"number","description":"Output token budget for this wait call. Defaults to 10000 tokens."},"terminate":{"type":"boolean","description":"True stops the running exec cell; false or omitted waits for output."},"yield_time_ms":{"type":"number","description":"Wait before yielding more output. Defaults to 10000 ms."}},"required":["cell_id"],"additionalProperties":false}},{"type":"function","name":"request_user_input","description":"Request user input for one to three short questions and wait for the response. This tool is only available in Plan mode.","strict":false,"parameters":{"type":"object","properties":{"questions":{"type":"array","description":"Questions to show the user. Prefer 1 and do not exceed 3","items":{"type":"object","properties":{"header":{"type":"string","description":"Short header label shown in the UI (12 or fewer chars)."},"id":{"type":"string","description":"Stable identifier for mapping answers (snake_case)."},"options":{"type":"array","description":"Provide 2-3 mutually exclusive choices. Put the recommended option first and suffix its label with \\"(Recommended)\\". Do not include an \\"Other\\" option in this list; the client will add a free-form \\"Other\\" option automatically.","items":{"type":"object","properties":{"description":{"type":"string","description":"One short sentence explaining impact/tradeoff if selected."},"label":{"type":"string","description":"User-facing label (1-5 words)."}},"required":["label","description"],"additionalProperties":false}},"question":{"type":"string","description":"Single-sentence prompt shown to the user."}},"required":["id","header","question","options"],"additionalProperties":false}}},"required":["questions"],"additionalProperties":false}},{"type":"function","name":"request_user_input_async","description":"Ask the user one or more questions during ongoing work. Use this tool only to request missing information, preferences, constraints, clarification, or approval. The tool returns immediately without ending the turn or waiting for a reply; any reply arrives asynchronously as a new user message. Keep questions concise, self-contained, and easy to understand, using a level of detail appropriate to the user and task. The UI always allows a free-text answer, including when suggested options are provided. A preselected option is not submitted automatically.","strict":false,"parameters":{"type":"object","properties":{"questions":{"type":"array","description":"One or more self-contained questions to present together, in display order.","items":{"type":"object","properties":{"options":{"type":"array","description":"Suggested answers, in display order. Put the recommended answer first; the first option is preselected by default. The user can select one option or enter a free-text answer. Do not include an Other option or a free-text placeholder; the UI provides free-text input automatically. Omit options for a free-text-only question.","items":{"type":"string"},"minItems":1},"title":{"type":"string","description":"The complete question shown to the user, including any context needed to answer it."}},"required":["title"],"additionalProperties":false},"minItems":1}},"required":["questions"],"additionalProperties":false}}]},{"type":"namespace","name":"clock","description":"Tools for reading and waiting on time.","tools":[{"type":"function","name":"sleep","description":"Pause execution for a specified duration. The sleep ends early when new input arrives for the active turn. Returns the elapsed wall-clock time.","strict":false,"parameters":{"type":"object","properties":{"duration_ms":{"type":"number","description":"How long to sleep in milliseconds. Must be between 1 and 43200000."}},"required":["duration_ms"],"additionalProperties":false}}]},{"type":"namespace","name":"collaboration","description":"Tools for spawning and managing sub-agents.","tools":[{"type":"function","name":"followup_task","description":"Send a follow-up task to an existing non-root target agent and trigger a turn if it is idle. If the target is already running, deliver the task promptly at message boundaries while sampling, or after the pending tool call completes.","strict":false,"parameters":{"type":"object","properties":{"message":{"type":"string","description":"Message text to send to the target agent.","encrypted":true},"target":{"type":"string","description":"Agent id or canonical task name to send a follow-up task to (from spawn_agent)."}},"required":["target","message"],"additionalProperties":false}},{"type":"function","name":"interrupt_agent","description":"Interrupt an agent\'s current turn, if any, and return its previous status. The agent remains available for messages and follow-up tasks.","strict":false,"parameters":{"type":"object","properties":{"target":{"type":"string","description":"Agent id or canonical task name to interrupt (from spawn_agent)."}},"required":["target"],"additionalProperties":false}},{"type":"function","name":"list_agents","description":"List live agents in the current root thread tree. Optionally filter by task-path prefix.","strict":false,"parameters":{"type":"object","properties":{"path_prefix":{"type":"string","description":"Task-path prefix filter without a trailing slash. Omit to list all live agents."}},"additionalProperties":false}},{"type":"function","name":"send_message","description":"Send a message to an existing agent. The message will be delivered promptly. Does not trigger a new turn.","strict":false,"parameters":{"type":"object","properties":{"message":{"type":"string","description":"Message text to queue on the target agent.","encrypted":true},"target":{"type":"string","description":"Relative or canonical task name to message (from spawn_agent)."}},"required":["target","message"],"additionalProperties":false}},{"type":"function","name":"spawn_agent","description":"\\n        Available model overrides (optional; inherited parent model is preferred):\\n- `gpt-6.1-sol`: Latest workhorse model for coding and everyday work. Reasoning efforts: low (default), medium, high, xhigh, max, ultra. Service tiers: priority.\\n- `gpt-6-astra`: Frontier intelligence for the most demanding work. Reasoning efforts: low, medium (default), high, xhigh, max, ultra. Service tiers: priority.\\n- `gpt-6.1-terra`: GPT-6.1 Terra Codex model. Reasoning efforts: low (default), medium, high, xhigh, max, ultra. Service tiers: priority.\\n- `gpt-6-sol`: Previous generation workhorse model. Reasoning efforts: low, medium (default), high, xhigh, max, ultra. Service tiers: priority.\\n- `gpt-6-luna`: Fast and affordable model for easier tasks. Reasoning efforts: low, medium (default), high, xhigh, max. Service tiers: priority.\\n        Spawns an agent to work on the specified task. If your current task is `/root/task1` and you spawn_agent with task_name \\"task_3\\" the agent will have canonical task name `/root/task1/task_3`.\\nYou are then able to refer to this agent as `task_3` or `/root/task1/task_3` interchangeably. However an agent `/root/task2/task_3` would only be able to communicate with this agent via its canonical name `/root/task1/task_3`.\\nThe spawned agent will have the same tools as you and the ability to spawn its own subagents.\\n\\nIt will be able to send you and other running agents messages, and its final answer will be provided to you when it finishes.\\nThe new agent\'s canonical task name will be provided to it along with the message.\\n\\nNote that passing `fork_turns=\\"none\\"` will not pass any surrounding context to the spawned subagent, which may cause the agent to lack the context it needs to complete its task, whereas `fork_turns=\\"all\\"` will provide the subagent with all surrounding context.","strict":false,"parameters":{"type":"object","properties":{"fork_turns":{"type":"string","description":"Parent history to inherit. Defaults to `all`; use `none` to start without parent history. Only `all` and `none` are supported."},"message":{"type":"string","description":"Initial plain-text task for the new agent.","encrypted":true},"model":{"type":"string","description":"Model override for the new agent. Omit unless an explicit override is needed."},"reasoning_effort":{"type":"string","description":"Reasoning effort override for the new agent. Omit to inherit the parent effort."},"task_name":{"type":"string","description":"Task name for the new agent. Use lowercase letters, digits, and underscores."}},"required":["task_name","message"],"additionalProperties":false}},{"type":"function","name":"wait_agent","description":"Wait for a mailbox update from any live agent, including queued messages and final-status notifications. The wait also ends early when new user input is steered into the active turn. Does not return the content; returns either a summary of which agents have updates (if any), an interruption summary for steered input, or a timeout summary if no activity arrives before the deadline.","strict":false,"parameters":{"type":"object","properties":{"timeout_ms":{"type":"number","description":"Timeout in milliseconds. Defaults to 30000, min 10000, max 3600000."}},"additionalProperties":false}}]}]'

def tools_namespaces() -> list[dict[str, Any]]:
    override = os.environ.get("CODEX_CLONE_TOOLS_JSON")
    if override:
        return load_json(Path(override))
    return json.loads(_EMBEDDED_TOOLS_JSON)


async def recv_until_completed(ws) -> dict[str, Any]:
    text_out: list[str] = []
    completed: dict[str, Any] | None = None
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=120)
        ev = json.loads(raw)
        t = ev.get("type")
        if t == "response.output_text.delta":
            text_out.append(ev.get("delta") or "")
        elif t == "response.output_text.done":
            if ev.get("text"):
                text_out = [ev["text"]]
        elif t == "response.completed":
            completed = ev
            break
        elif t in {"error", "response.failed"}:
            raise RuntimeError(json.dumps(ev)[:2000])
    assert completed is not None
    resp = completed.get("response") or {}
    return {
        "response_id": resp.get("id") or completed.get("response_id"),
        "text": "".join(text_out),
        "completed": completed,
    }


async def main(prompt: str) -> None:
    token, account_id = load_auth()
    cfg = load_config()
    model_slug = cfg.get("model", "gpt-6.1-sol")
    effort = cfg.get("model_reasoning_effort", "high")
    model = load_model(model_slug)
    base_instructions = model["model_messages"]["instructions_template"]
    collab = model["model_messages"]["collaboration_modes"]["default"]
    role_root = model["model_messages"]["multi_agent"]["role"]["root"]
    verbosity = model.get("default_verbosity") or "low"
    inst = installation_id()
    sandbox_mode = "read-only"
    cwd = Path("/tmp")

    session_id = str(uuid7())
    context_window_id = str(uuid7())
    window_id = f"{session_id}:0"
    ns = uuid_v5_oid(session_id.encode())

    headers = {
        "Authorization": f"Bearer {token}",
        "ChatGPT-Account-Id": account_id,
        "OpenAI-Beta": OPENAI_BETA,
        "Originator": ORIGINATOR if False else "codex_exec",  # match CLI for backend acceptance
        "Session-Id": session_id,
        "Version": CLI_VERSION,
        "User-Agent": user_agent(),
        "x-client-request-id": session_id,
        "x-codex-beta-features": "remote_compaction_v2",
        "x-codex-routing-hint": f"model={model_slug}",
        "x-codex-window-id": window_id,
        "x-codex-turn-metadata": turn_metadata(
            inst=inst,
            session_id=session_id,
            turn_id="",
            window_id=window_id,
            context_window_id=context_window_id,
            request_kind="prewarm",
            model=model_slug,
            effort=effort,
            sandbox_mode=sandbox_mode,
        ),
    }

    tools = tools_namespaces()
    tools_id = item_id_bytes("at", ns, json.dumps(tools, separators=(",", ":")).encode())
    base_id = item_id_bytes("msg", ns, base_instructions.encode())

    prewarm_input = [
        {
            "type": "additional_tools",
            "id": tools_id,
            "role": "developer",
            "tools": tools,
        },
        msg(
            role="developer",
            text_parts=[base_instructions],
            item_id=base_id,
            kinds=["model.base_instructions"],
        ),
    ]

    prewarm = {
        "type": "response.create",
        "model": model_slug,
        "stream": True,
        "input": prewarm_input,
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "reasoning": {"effort": effort, "context": "all_turns"},
        "store": False,
        "include": ["reasoning.encrypted_content"],
        "prompt_cache_key": session_id,
        "text": {"verbosity": verbosity},
        "generate": False,
        "client_metadata": client_metadata(
            inst=inst,
            session_id=session_id,
            turn_id="",
            window_id=window_id,
            context_window_id=context_window_id,
            request_kind="prewarm",
            model=model_slug,
            effort=effort,
            sandbox_mode=sandbox_mode,
        ),
    }

    turn_id = new_turn_id()
    turn_started = int(time.time() * 1000)
    now = time.time()

    host_bundle_parts = [
        build_skills_block(),
        build_permissions(sandbox_mode),
        wrap_collab(collab),
        recommended_plugins_from_capture(),
    ]
    host_id = item_id_bytes("msg", ns, "\n".join(host_bundle_parts).encode())
    role_id = item_id_bytes("msg", ns, (wrap_multi_agent_role(role_root) + turn_id).encode())
    mode_id = item_id_bytes("msg", ns, multi_agent_mode_off().encode())
    env_text = build_environment(cwd)
    env_id = item_id_bytes("msg", ns, env_text.encode())
    user_id = item_id_bytes("msg", ns, (prompt + turn_id).encode())

    turn_input = [
        msg(
            role="developer",
            text_parts=host_bundle_parts,
            item_id=host_id,
            kinds=[
                "host_skills.instructions",
                "permissions.instructions",
                "collaboration_mode.instructions",
                "plugins.recommendations",
            ],
            turn_id=turn_id,
            create_time=now,
        ),
        msg(
            role="developer",
            text_parts=[wrap_multi_agent_role(role_root)],
            item_id=role_id,
            kinds=["multi_agent.role_instructions"],
            turn_id=turn_id,
            create_time=now,
        ),
        msg(
            role="developer",
            text_parts=[multi_agent_mode_off()],
            item_id=mode_id,
            kinds=["multi_agent.mode_instructions"],
            turn_id=turn_id,
            create_time=now,
        ),
        msg(
            role="user",
            text_parts=[env_text],
            item_id=env_id,
            kinds=["environments.environment_context"],
            turn_id=turn_id,
            create_time=now,
        ),
        msg(
            role="user",
            text_parts=[prompt],
            item_id=user_id,
            kinds=["user.text"],
            turn_id=turn_id,
            create_time=now + 0.01,
        ),
    ]

    out_dir = Path("/workspace/codex-clone")
    out_dir.mkdir(parents=True, exist_ok=True)

    async with websockets.connect(
        WS_URL,
        additional_headers=headers,
        max_size=16 * 1024 * 1024,
        open_timeout=60,
    ) as ws:
        await ws.send(json.dumps(prewarm))
        warm = await recv_until_completed(ws)
        prev = warm["response_id"]
        if not prev:
            raise RuntimeError(f"prewarm missing response id: {json.dumps(warm)[:1000]}")

        turn_req = {
            "type": "response.create",
            "model": model_slug,
            "stream": True,
            "previous_response_id": prev,
            "input": turn_input,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "reasoning": {"effort": effort, "context": "all_turns"},
            "store": False,
            "include": ["reasoning.encrypted_content"],
            "prompt_cache_key": session_id,
            "text": {"verbosity": verbosity},
            "client_metadata": client_metadata(
                inst=inst,
                session_id=session_id,
                turn_id=turn_id,
                window_id=window_id,
                context_window_id=context_window_id,
                request_kind="turn",
                model=model_slug,
                effort=effort,
                sandbox_mode=sandbox_mode,
                turn_started_at_unix_ms=turn_started,
            ),
            "access_programs": {"cyber": "standard"},
        }
        # redact tokens in saved request
        saved = {
            "headers": {k: ("<redacted>" if k.lower() == "authorization" else v) for k, v in headers.items()},
            "prewarm": prewarm,
            "turn": turn_req,
        }
        (out_dir / "last_request.json").write_text(json.dumps(saved, indent=2, ensure_ascii=False))

        await ws.send(json.dumps(turn_req))
        result = await recv_until_completed(ws)

    summary = {
        "ok": True,
        "session_id": session_id,
        "turn_id": turn_id,
        "prewarm_response_id": prev,
        "turn_response_id": result["response_id"],
        "assistant_text": result["text"],
        "field_sources": {
            "authorization": "~/.codex/auth.json tokens.access_token",
            "chatgpt-account-id": "~/.codex/auth.json tokens.account_id",
            "installation_id": "~/.codex/installation_id",
            "model/verbosity/instructions": "~/.codex/models_cache.json + config.toml",
            "reasoning.effort": "config.toml model_reasoning_effort",
            "session/turn/window ids": "uuid7()",
            "item ids (msg_/at_)": "uuid5(NAMESPACE_OID(session), content_bytes)",
            "prompt_cache_key": "session_id",
            "tools": "live_tools.json (full namespace schemas from Codex wire capture)",
            "skills": "scan ~/.codex/skills/.system",
            "environment": "cwd/date/timezone computed",
        },
    }
    (out_dir / "last_result.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]).strip() or os.environ.get("CODEX_CLONE_PROMPT") or "Reply with exactly: OK"
    asyncio.run(main(prompt))
