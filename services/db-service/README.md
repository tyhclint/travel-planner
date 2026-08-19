# Database Service (FastAPI + MongoDB)

Dedicated persistence microservice managing trip itineraries, conversation thread checkpoints, and user bookmarks via MongoDB (Motor async driver).

## Port
- Default Port: `8002`

## Endpoints
- `GET /api/trips`: List user trips.
- `POST /api/trips`: Create or save a new trip.
- `GET /api/trips/{trip_id}`: Retrieve trip by ID.
- `PUT /api/trips/{trip_id}`: Update trip contents.
- `DELETE /api/trips/{trip_id}`: Delete a trip.
- `GET /api/conversations/{thread_id}`: Get conversation state checkpoint.
- `POST /api/conversations/{thread_id}`: Save conversation state checkpoint.
- `GET /api/bookmarks`, `POST /api/bookmarks`: Manage flight/hotel bookmarks.
- `GET /health`: Database connectivity health check.

## Run Locally
```bash
uv run uvicorn app.main:app --port 8002 --reload
```

## Run Tests
```bash
uv run pytest
```
