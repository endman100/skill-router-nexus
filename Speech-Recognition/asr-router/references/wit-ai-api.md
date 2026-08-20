# Wit.ai

**Type:** **API** through the installed Rube MCP/Composio toolkit.

```text
RUBE_SEARCH_TOOLS
queries: [{use_case: "Recognize speech audio with Wit.ai and return transcript data", known_fields: ""}]
session: {generate_id: true}
```

Check `RUBE_MANAGE_CONNECTIONS` with toolkit `wit_ai`, require `ACTIVE`, then
execute the discovered tool through `RUBE_MULTI_EXECUTE_TOOL` with its exact
live schema, `memory: {}`, and the same session. Do not hardcode tool slugs.

Wit.ai may return intent/entity data. Map only real ASR transcript and timing
fields; preserve the complete response as the raw artifact.

Source ASR workflow migrated from `Speech-Recognition/wit-ai-automation`;
that skill retains non-ASR Wit.ai automation.
