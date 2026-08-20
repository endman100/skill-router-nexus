# Rev AI

**Type:** **API** through the installed Rube MCP/Composio toolkit.

```text
RUBE_SEARCH_TOOLS
queries: [{use_case: "Transcribe audio with Rev AI and return the requested timestamp granularity", known_fields: ""}]
session: {generate_id: true}
```

Check `RUBE_MANAGE_CONNECTIONS` with toolkit `rev_ai`, require `ACTIVE`, then
execute the discovered tool through `RUBE_MULTI_EXECUTE_TOOL` with the exact
live schema, `memory: {}`, and the same session. Follow asynchronous polling and
pagination. Do not hardcode slugs or arguments.

Source ASR workflow migrated from `Speech-Recognition/rev-ai-automation`;
that skill retains non-ASR operations.
