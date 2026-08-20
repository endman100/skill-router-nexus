# Gladia

**Type:** **API** through the installed Rube MCP/Composio toolkit.

```text
RUBE_SEARCH_TOOLS
queries: [{use_case: "Transcribe audio with Gladia; include required timestamps or realtime behavior", known_fields: ""}]
session: {generate_id: true}
```

Check `RUBE_MANAGE_CONNECTIONS` with toolkit `gladia`, require `ACTIVE`, then
execute the discovered tool through `RUBE_MULTI_EXECUTE_TOOL` using its exact
schema, `memory: {}`, and the same session. Follow returned polling or
pagination and do not hardcode tool slugs.

Source ASR workflow migrated from `Speech-Recognition/gladia-automation`;
that skill retains non-ASR Gladia automation.
