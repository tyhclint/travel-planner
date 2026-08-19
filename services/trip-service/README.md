# Trip Service (FastAPI + Trip.com Scraping / API)

Dedicated provider microservice responsible for flight searches, accommodation searches, and destination points of interest research, wrapping Trip.com web data / API sources with deterministic fallback capabilities.

## Port
- Default Port: `8003`

## Endpoints
- `POST /api/flights/search`: Query flights by origin, destination, dates, and cabin class.
- `POST /api/accommodations/search`: Query hotels by destination, dates, budget, and preferences.
- `POST /api/destinations/research`: Discover destination highlights, activities, and attractions.
- `GET /health`: Health check endpoint.

## Run Locally
```bash
uv run uvicorn app.main:app --port 8003 --reload
```

## Run Tests
```bash
uv run pytest
```
