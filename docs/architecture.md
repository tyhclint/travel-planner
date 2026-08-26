# Travel Planner Microservices Architecture

This document describes the architectural topology, service responsibilities, and communication patterns of the `travel-planner` backend.

```mermaid
graph TD
    Client["Next.js Frontend (Port 3000)"]
    Gateway["API Gateway (FastAPI, Port 8000)"]
    AgentService["Agent Service (FastAPI + LangGraph, Port 8001)"]
    DBService["DB Service (FastAPI + MongoDB, Port 8002)"]
    TripService["Trip Service (FastAPI + Trip.com Scraping, Port 8003)"]
    Mongo[("MongoDB Database (Port 27017)")]

    Client -->|HTTP / NDJSON Stream| Gateway
    Gateway -->|Proxy /travel/stream| AgentService
    Gateway -->|Proxy /trips CRUD| DBService
    Gateway -->|Proxy /search endpoints| TripService

    AgentService -->|Fetch Flights/Hotels/POIs| TripService
    AgentService -->|Save State Checkpoints| DBService

    DBService -->|Motor Async Driver| Mongo
```

---

## Service Overview

### 1. Gateway (`services/gateway`, Port `8000`)
- **Role**: Single entrypoint for external clients (Next.js web app / mobile).
- **Key Responsibilities**:
  - Routing and request forwarding.
  - CORS header handling.
  - Streaming pass-through (`x-ndjson`) from the LangGraph agent to the client.
  - Aggregated system health checks.

### 2. Agent Service (`services/agent-service`, Port `8001`)
- **Role**: Intelligent agent orchestration engine.
- **Key Responsibilities**:
  - LangGraph state machine execution (`turn_interpreter` -> `task_status` -> `orchestrator` -> specialists -> `ranking` -> `itinerary_planner` -> `response_agent`).
  - Deterministic dependency invalidation (marking tasks `stale` when inputs change).
  - Multi-turn conversation management with checkpointing.
  - Inter-service communication with `trip-service` for data gathering and `db-service` for persistence.

### 3. DB Service (`services/db-service`, Port `8002`)
- **Role**: Persistence and state store.
- **Key Responsibilities**:
  - MongoDB CRUD operations using the asynchronous `motor` driver.
  - Storage for saved trips, itinerary days, bookmarks, and conversation thread checkpoints.

### 4. Trip Service (`services/trip-service`, Port `8003`)
- **Role**: Travel data provider adapter.
- **Key Responsibilities**:
  - Real-time / mock scraping for flights and hotels on Trip.com.
  - Destination POI and cultural recommendations.
  - Isolated dependency boundary (BeautifulSoup, scraping logic, rate-limiting guards).

---

## Inter-Service Interaction Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Next.js Client
    participant GW as API Gateway (8000)
    participant AG as Agent Service (8001)
    participant TS as Trip Service (8003)
    participant DB as DB Service (8002)

    User->>GW: POST /api/travel/stream {thread_id, message}
    GW->>AG: POST /api/travel/stream {thread_id, message}
    
    AG->>AG: turn_interpreter extracts intent & requirements
    AG->>AG: task_status invalidates stale tasks
    AG->>AG: orchestrator plans next subagent tasks
    
    par Parallel Specialist Tasks
        AG->>TS: POST /api/flights/search
        TS-->>AG: FlightOption list
    and
        AG->>TS: POST /api/accommodations/search
        TS-->>AG: AccommodationOption list
    and
        AG->>TS: POST /api/destinations/research
        TS-->>AG: DestinationRecommendation list
    end

    AG->>AG: fan_in -> ranking -> itinerary_planner -> response_agent
    AG->>DB: POST /api/conversations/{thread_id} (checkpoint state)
    DB-->>AG: 200 OK

    AG-->>GW: stream ndjson updates & final response
    GW-->>User: stream ndjson events to UI
```
