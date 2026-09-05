# Travel Planner Backend (Microservices Architecture)

An agentic, multi-turn AI travel planner backend built with **LangGraph**, **FastAPI**, **MongoDB**, and **Docker Compose**.

```text
travel-planner/
├── services/
│   ├── agent-service/       # FastAPI + LangGraph Agent & Orchestrator Engine (Port 8001)
│   │   ├── app/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── gateway/              # FastAPI API Gateway routing from Next.js (Port 8000)
│   │   ├── app/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── db-service/           # FastAPI + MongoDB persistence service (Port 8002)
│   │   ├── app/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   └── trip-service/         # FastAPI + Trip.com scraping / API provider (Port 8003)
│       ├── app/
│       ├── tests/
│       ├── Dockerfile
│       └── pyproject.toml
│
├── docker-compose.yml         # Spins up all 4 services + Mongo for local dev
├── .env.example               # Environment variables template
├── docs/                      # Architecture notes & inter-service API contracts
└── README.md
```

---

## Service Port Mapping

| Service | Port | Description |
|---|---|---|
| **Gateway** | `8000` | Public API surface for Next.js frontend, routing, CORS, and NDJSON streaming proxy. |
| **Agent Service** | `8001` | LangGraph multi-turn planner, state machine, ranking, and synthesis. |
| **DB Service** | `8002` | MongoDB CRUD operations for trips, conversation threads, and bookmarks. |
| **Trip Service** | `8003` | Flight, accommodation, and POI discovery adapter (Trip.com scraping / mock fallback). |
| **MongoDB** | `27017` | Local persistent database container. |

---

## Quick Start with Docker Compose

To spin up all 4 microservices and the MongoDB database with a single command:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Build and start containers
docker compose up --build
```

Access the API Gateway interactive documentation at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## Running Services Individually (Local Development with `uv`)

Each microservice is an independent Python package with its own dependencies and `pyproject.toml`.

### 1. Gateway (`services/gateway`)
```bash
cd services/gateway
uv run uvicorn app.main:app --port 8000 --reload
```

### 2. Agent Service (`services/agent-service`)
```bash
cd services/agent-service
uv run uvicorn app.main:app --port 8001 --reload
```

### 3. DB Service (`services/db-service`)
```bash
cd services/db-service
uv run uvicorn app.main:app --port 8002 --reload
```

### 4. Trip Service (`services/trip-service`)
```bash
cd services/trip-service
uv run uvicorn app.main:app --port 8003 --reload
```

---

## Running Tests

Run test suites for any microservice independently:

```bash
# Test Agent Service
cd services/agent-service
uv run pytest

# Test Gateway Service
cd services/gateway
uv run pytest

# Test DB Service
cd services/db-service
uv run pytest

# Test Trip Service
cd services/trip-service
uv run pytest
```

---

## Frontend Integration (Next.js)

The Next.js client connects exclusively to the **API Gateway** on `http://localhost:8000`:

- **Streaming Plan Generation**: `POST http://localhost:8000/api/travel/stream`
  ```json
  {
    "thread_id": "user-123-tokyo-trip",
    "message": "Plan me a cheap 5-day trip from Singapore to Tokyo"
  }
  ```
- **List / Save Trips**: `GET /api/trips`, `POST /api/trips`
- **Direct Search**: `POST /api/search/flights`, `POST /api/search/accommodations`
