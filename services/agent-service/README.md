# Agent Service (FastAPI + LangGraph)

LangGraph orchestration microservice responsible for conversational trip planning, multi-turn state checkpointing, domain specialist subagents, ranking, and response synthesis.

## Port
- Default Port: `8001`

## Endpoints
- `POST /api/travel/stream`: Streaming ndjson state updates for the user prompt.
- `POST /api/travel/invoke`: Synchronous graph invocation returning the final state.
- `GET /health`: Health check endpoint.

## Run Locally
```bash
uv run uvicorn app.main:app --port 8001 --reload
```

## Run Tests
```bash
uv run pytest
```
