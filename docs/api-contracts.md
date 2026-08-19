# Inter-Service API Contracts & Schemas

This document defines the REST and streaming API contracts exposed by each microservice in the system.

---

## 1. Gateway (`services/gateway` : `8000`)

### `POST /api/travel/stream`
- **Description**: Proxies NDJSON stream directly from `agent-service`.
- **Request Body**:
  ```json
  {
    "thread_id": "user-123-tokyo",
    "message": "Plan me a 5-day trip to Tokyo"
  }
  ```
- **Response**: `application/x-ndjson` stream of state graph updates.

### `POST /api/travel/invoke`
- **Description**: Synchronous execution returning the final response.
- **Request Body**:
  ```json
  {
    "thread_id": "user-123-tokyo",
    "message": "Plan me a 5-day trip to Tokyo"
  }
  ```
- **Response** `200 OK`:
  ```json
  {
    "thread_id": "user-123-tokyo",
    "final_response": "Top flight: Singapore Airlines...\nTop stay: Shibuya Hotel...",
    "task_status": {
      "flight": "completed",
      "accommodation": "completed",
      "ranking": "completed",
      "destination_research": "completed",
      "itinerary": "completed"
    }
  }
  ```

### `GET /api/trips` / `POST /api/trips`
- Proxies to `db-service` trip endpoints.

### `POST /api/search/flights` / `POST /api/search/accommodations`
- Proxies to `trip-service` search endpoints.

---

## 2. Agent Service (`services/agent-service` : `8001`)

### `POST /api/travel/stream`
- **Header**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "thread_id": "string",
    "message": "string"
  }
  ```
- **Output**: `application/x-ndjson` stream where each line contains `{node_name: partial_state_update}`.

### `POST /api/travel/invoke`
- **Output**: Final `TravelState` snapshot and synthesized response.

---

## 3. Database Service (`services/db-service` : `8002`)

### `GET /api/trips?user_id={id}`
- **Response**: Array of trip objects.

### `POST /api/trips`
- **Request Body**:
  ```json
  {
    "user_id": "user-123",
    "title": "5 Days in Tokyo",
    "destination": "Tokyo",
    "origin": "Singapore",
    "trip_length_days": 5,
    "itinerary": {
      "days": []
    }
  }
  ```

### `GET /api/conversations/{thread_id}`
- **Response**: Conversation checkpoints, message log, and serialized graph state.

---

## 4. Trip Service (`services/trip-service` : `8003`)

### `POST /api/flights/search`
- **Request Body**:
  ```json
  {
    "origin": "Singapore",
    "destination": "Tokyo",
    "departure_date": "2026-10-01",
    "return_date": "2026-10-06",
    "cabin_class": "economy",
    "currency": "USD"
  }
  ```
- **Response** `200 OK`:
  ```json
  {
    "origin": "Singapore",
    "destination": "Tokyo",
    "flights": [
      {
        "id": "fl-trip-1",
        "airline": "Singapore Airlines",
        "origin": "Singapore",
        "destination": "Tokyo",
        "departure_time": "2026-10-01T08:00:00Z",
        "arrival_time": "2026-10-01T15:00:00Z",
        "duration_minutes": 420,
        "stops": 0,
        "cabin_class": "economy",
        "total_price": 540.0,
        "currency": "USD",
        "provider": "Trip.com",
        "booking_url": "https://www.trip.com/flights/Singapore-to-Tokyo"
      }
    ]
  }
  ```

### `POST /api/accommodations/search`
- **Request Body**:
  ```json
  {
    "destination": "Tokyo",
    "accommodation_style": "standard",
    "accommodation_priority": "balanced",
    "currency": "USD"
  }
  ```
- **Response** `200 OK`:
  ```json
  {
    "destination": "Tokyo",
    "accommodations": [
      {
        "id": "acc-trip-1",
        "name": "Tokyo Shibuya Sky View Hotel",
        "accommodation_type": "hotel",
        "location": "Shibuya, Tokyo",
        "rating": 4.6,
        "nightly_price": 140.0,
        "total_price": 560.0,
        "currency": "USD",
        "amenities": ["Free High-Speed WiFi", "Walking distance to metro"],
        "provider": "Trip.com"
      }
    ]
  }
  ```

### `POST /api/destinations/research`
- **Request Body**:
  ```json
  {
    "destination": "Tokyo",
    "interests": ["culture", "food"],
    "pace": "balanced"
  }
  ```
- **Response** `200 OK`:
  ```json
  {
    "destination": "Tokyo",
    "recommendations": [
      {
        "name": "Senso-ji Temple",
        "category": "culture",
        "description": "Ancient Buddhist temple in Asakusa",
        "location": "Asakusa, Tokyo",
        "estimated_cost": 0.0,
        "source_url": "https://www.trip.com/travel-guide/attraction/tokyo/senso-ji-10524185/"
      }
    ]
  }
  ```
