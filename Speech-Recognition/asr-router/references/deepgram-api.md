# Deepgram

**Type:** **API** through the installed Rube MCP/Composio toolkit.

```text
RUBE_SEARCH_TOOLS
queries: [{use_case: "Transcribe audio with Deepgram; return the requested timestamps or realtime stream", known_fields: ""}]
session: {generate_id: true}
```

Check `RUBE_MANAGE_CONNECTIONS` with toolkit `deepgram`; require `ACTIVE`.
Execute the discovered transcription tool with `RUBE_MULTI_EXECUTE_TOOL`, exact
discovered arguments, `memory: {}`, and the same session ID. Follow returned
polling or pagination. Do not hardcode tool slugs or stale field names.

Source ASR workflow migrated from `Speech-Recognition/deepgram-automation`;
that skill retains non-ASR Deepgram automation.
