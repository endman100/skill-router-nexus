---
name: codex-browser-tool-priority
description: "Use when Codex needs to open, inspect, navigate, click, type, screenshot, test, or debug a web page or browser-based workflow and multiple UI automation surfaces are available. Enforces Codex tool priority: use the Chrome plugin first, fall back to Computer Use only when Chrome cannot handle the task, and use the Browser plugin only as the last fallback or when the user explicitly requests Browser."
---

# Codex Browser Tool Priority

## Overview

Use this skill to choose the correct UI automation surface in Codex before any browser testing or browser operation. The default priority is:

1. Chrome plugin: `@chrome` / `plugin://chrome@openai-bundled`
2. Computer Use plugin: `@電腦` / `plugin://computer-use@openai-bundled`
3. Browser plugin: `@瀏覽器` / `plugin://browser@openai-bundled`

Do not start with Browser just because it is isolated or convenient. Browser is the fallback after Chrome and Computer Use are ruled out, unless the user explicitly asks for Browser.

## Decision Rule

### Step 1: Try Chrome First

Use Chrome when the task involves:

- The user's existing Chrome state, tabs, cookies, extensions, or logged-in sessions.
- Testing a real site, staging site, production page, localhost app, or web workflow where the user expects to see or preserve Chrome state.
- Clicking, typing, navigating, inspecting visible browser state, or taking screenshots from the user's Chrome context.
- Debugging behavior that may differ between an isolated browser and the user's actual browser.

If the Chrome plugin tools are not loaded, use tool discovery first when available. If Chrome is available but not authenticated or connected, ask the user to reconnect or approve the fallback before switching tools.

### Step 2: Fall Back to Computer Use

Use Computer Use only after Chrome is unavailable or insufficient.

Valid reasons to switch from Chrome to Computer Use:

- Chrome plugin is not callable in the current Codex session.
- Chrome cannot access or control the required window, tab, modal, file picker, permission prompt, or extension UI.
- The task crosses outside Chrome into the OS, another desktop app, a native dialog, or a screen area only visible through desktop control.
- Chrome repeatedly fails after a concrete retry and the visible desktop can still complete the task.

Computer Use is a desktop-control fallback, not the default browser testing tool. Use it with narrow, visible actions and verify the result from the screen.

### Step 3: Use Browser Last

Use Browser only when:

- Chrome and Computer Use are unavailable, blocked, or inappropriate for the task.
- The user explicitly requests `@browser`, `@瀏覽器`, Browser, or the in-app browser.
- The task is better served by an isolated browser session and does not need the user's Chrome cookies, tabs, extensions, or desktop state.

When using Browser as fallback, state why Chrome and Computer Use were not used.

## Failure Handling

Before downgrading tools, record the concrete blocker:

- `Chrome unavailable`: plugin tools are not present or cannot be loaded.
- `Chrome disconnected`: tool reports missing or expired connection.
- `Chrome insufficient`: required UI is outside Chrome control.
- `Computer Use unavailable`: desktop tool is not present or cannot see/control the needed surface.
- `Browser explicit`: user explicitly requested Browser.

Do not silently change surfaces. A fallback changes evidence quality and browser state, so mention it briefly in the working update or final report.

## Verification

For browser testing or UI debugging, verify on the same surface used for the final claim:

- If the claim depends on the user's session, verify in Chrome.
- If the claim depends on desktop UI state, verify with Computer Use.
- If the claim only depends on an isolated app render, Browser verification is acceptable after the fallback reason is stated.

When reporting results, include the surface used, the target URL or app surface, and the visible evidence checked, such as page title, URL, screenshot, DOM state, or user-visible success/error state.
