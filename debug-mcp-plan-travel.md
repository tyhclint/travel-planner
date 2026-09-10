nt# Debug Session: mcp-plan-travel

Status: OPEN

## Symptom

- MCP initialization succeeds.
- MCP `tools/call` for `plan_travel` returns `Error executing tool plan_travel`.
- The server is reachable, so the failure is inside the tool execution path.

## Initial Hypotheses

1. `run_travel_turn()` raises before producing a response, and the MCP layer swallows the original exception.
2. The LangGraph workflow is failing because one of its downstream services or graph nodes is misconfigured at runtime.
3. The travel workflow still depends on unavailable credentials or network services during the `plan_travel` path.
4. The MCP tool wrapper is returning a type or payload shape that MCP 2.x rejects after the tool function runs.
5. The eager BAAI/RAG initialization path is interfering with `plan_travel` execution when the graph touches destination search.

## Next Step

- Add instrumentation at the MCP tool boundary to capture the real exception and request context for `plan_travel`.
