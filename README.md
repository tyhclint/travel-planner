# travel-planner

LangGraph-powered travel planner microservice skeleton.

## Run the CLI smoke demo

```powershell
uv run python main.py
```

## Run the FastAPI server

```powershell
uv run uvicorn app.main:app --reload
```

The initial streaming-shaped endpoint is:

```text
POST /api/travel/stream
```

Example body:

```json
{
  "thread_id": "user-123-tokyo-trip",
  "message": "Plan me a cheap 5-day trip from Singapore to Tokyo"
}
```

The graph currently uses mock providers. Real APIs or MCP-backed services can be added under
`app/services/` without changing the graph node contracts.
