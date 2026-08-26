# Gateway Service (FastAPI)

Unified API Gateway routing frontend requests from the Next.js client to internal microservices (`agent-service`, `trip-service`, and `db-service`).

## Port
- Default Port: `8000`

## Endpoints
- `POST /api/travel/stream`: Proxy ndjson streaming connection to `agent-service`.
- `POST /api/travel/invoke`: Proxy synchronous invocation to `agent-service`.
- `GET /api/trips`, `POST /api/trips`, `GET /api/trips/{id}`: Proxy trip CRUD to `db-service`.
- `POST /api/search/flights`, `POST /api/search/accommodations`, `POST /api/search/destinations`: Direct search endpoints proxying to `trip-service`.
- `GET /health`: Aggregated health check reporting gateway & downstream services status.

## Run Locally
```bash
uv run uvicorn app.main:app --port 8000 --reload
```

## Run Tests
```bash
uv run pytest
```
