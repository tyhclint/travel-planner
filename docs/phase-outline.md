# Travel Planner LangGraph Microservice Phase Outline

This document summarizes the phased build plan for the travel planner repo after Phase 1.

The intended final system is a LangGraph-powered travel planner microservice with a FastAPI API layer. It will support multi-turn travel planning, specialist subagents, MCP/API-backed travel tools, dependency invalidation, itinerary revision, checkpointed state, and streaming responses to a future frontend.

## Current Architecture Direction

The app should follow a hybrid agentic architecture:

- Turn interpreter extracts structured user intent, trip facts, preferences, constraints, changed fields, and revision targets.
- Dependency invalidation deterministically marks existing artifacts as stale when their inputs change.
- Orchestrator acts as the central routing hub.
- Specialist subagents handle bounded domains such as flights, accommodations, web search, and itinerary planning.
- Ranking, validation, status transitions, and dependency rules should stay mostly deterministic.
- Response agent generates the final user-facing answer from structured state.

For the final design, the orchestrator may become hybrid:

- Deterministic rules for obvious routing, guardrails, retry limits, missing fields, and allowed next tasks.
- Optional LLM reasoning for ambiguous sufficiency decisions, follow-up planning, and deciding whether more specialist calls are needed.

The turn interpreter and orchestrator should not duplicate work:

- Turn interpreter answers: "What did the user say and what changed?"
- Orchestrator answers: "Given the current structured state, what should run next?"

## Phase 1: Runnable Skeleton, Done

Goal: prove the system shape works.

Completed:

- `uv` Python project setup.
- Root `pyproject.toml` and `uv.lock`.
- FastAPI app shell.
- LangGraph graph builder.
- Initial `TravelState`.
- Initial Pydantic domain models.
- Mock flight, accommodation, and search services.
- Basic dependency invalidation.
- Basic deterministic orchestrator.
- Basic fan-out/fan-in shape for flight and accommodation.
- Basic ranking.
- Mock itinerary generation.
- Mock response generation.
- CLI smoke demo through `main.py`.
- Test setup with `pytest`.
- Code quality check with `ruff`.

Current checks:

```powershell
uv run pytest
uv run ruff check .
uv run python main.py
```

Current tests verify:

- Full-trip graph flow works.
- Flight-only routing does not run accommodation.
- Accommodation-only routing does not run flight.
- Current flight ranking is price-based.

Phase 1 focus was not smart node logic. It was:

- Graph compiles.
- Graph reaches `END`.
- Basic routing works.
- State moves through nodes correctly.
- Mock providers and response path work.
- Service/domain/graph boundaries are in place.

## Phase 2: Solidify Graph Control Logic

Goal: make the deterministic backbone reliable before adding serious LLM calls or real providers.

Main work:

- Finalize the concrete `TravelState` fields.
- Finalize task status lifecycle.
- Finalize dependency invalidation rules.
- Improve routing logic.
- Add stronger tests around status changes and routing.
- Define clearer node input/output contracts.
- Improve the simple parser only enough to support deterministic tests.

Task status lifecycle:

```text
not_required
-> pending
-> running
-> completed
-> stale
-> running
-> completed
```

Also support:

```text
failed
```

Phase 2 should answer:

- What state fields exist?
- What does each node read?
- What does each node write?
- When does each task become `pending`?
- When does each task become `stale`?
- When should the graph rerun flight, accommodation, search, ranking, or itinerary?
- When should the graph skip those tasks?
- When should clarification happen?
- When can the response node run?

Important tests to add:

- Destination changed marks flight, accommodation, web search, ranking, and itinerary stale.
- Origin changed marks flight, ranking, and itinerary stale.
- Travel dates changed marks flight, accommodation, web search, ranking, and itinerary stale.
- Accommodation preference changed marks accommodation, ranking, and itinerary stale.
- Flight preference changed marks flight, ranking, and itinerary stale.
- Activity preference changed marks itinerary stale, and maybe web search depending on chosen rule.
- Day-specific itinerary edit marks itinerary stale only.
- Presentation-only request routes directly to response.
- Missing origin for flight request routes to clarification.
- Missing destination routes to clarification.
- Destination recommendation request routes to web search only.
- Existing completed flight remains completed when user only edits hotel.
- Existing completed hotel remains completed when user only edits flight.

Node logic can still be mock/simple in Phase 2. The point is reliable control flow.

## Phase 3: Lightweight LLM Turn Interpreter

Goal: replace keyword parsing with a structured LLM extraction call.

The turn interpreter should extract:

- `turn_type`
- `intent_summary`
- `trip_requirements`
- `preferences`
- `constraints`
- `changed_fields`
- `revision_targets`
- `latest_feedback`
- `missing_required_fields`

It should not:

- Call tools.
- Search providers.
- Decide the full workflow.
- Generate the final response.

Example itinerary revision input:

```text
Day 2 is too packed. Remove the museum and add shopping instead.
```

Example turn interpreter output:

```json
{
  "turn_type": "revision",
  "intent_summary": "User wants Day 2 to be less packed, remove the museum, and add shopping.",
  "trip_requirement_updates": {},
  "preference_updates": {
    "activity_pace": "relaxed",
    "interests_to_add": ["shopping"]
  },
  "constraints": {
    "preserve_flights": true,
    "preserve_accommodation": true,
    "preserve_unaffected_itinerary_days": true
  },
  "changed_fields": ["activity_preferences", "itinerary_day_2"],
  "revision_targets": [
    {
      "artifact": "itinerary",
      "scope": "day",
      "day": 2
    }
  ],
  "latest_feedback": {
    "remove": ["museum"],
    "add": ["shopping"],
    "instruction": "Make Day 2 less packed."
  },
  "missing_required_fields": []
}
```

This output lets dependency invalidation deterministically mark the right tasks as stale.

## Phase 4: Orchestrator Upgrade

Goal: make orchestration production-shaped.

The orchestrator is the central hub:

```text
orchestrator
-> subagent / clarification / response
-> orchestrator again if more work may be needed
```

It decides:

- Which subagent should run next.
- Whether stale work must be regenerated now.
- Whether results are sufficient.
- Whether to retry.
- Whether to call a fallback provider/subagent.
- Whether to ask the user for clarification.
- Whether the response node can run.

Recommended final design:

- Start deterministic.
- Upgrade to hybrid only when needed.

Hybrid orchestrator shape:

- Deterministic policy provides guardrails.
- Optional structured LLM decision handles ambiguous sufficiency and planning.

Example structured orchestrator output:

```json
{
  "next_tasks": ["web_search_agent"],
  "reason": "The existing destination research is too generic for the user's request for unique local shopping areas.",
  "can_answer_now": false
}
```

Guardrails:

- If `missing_required_fields` exists, route to clarification.
- If max orchestration steps exceeded, stop safely.
- Only allow known next tasks.
- Completed/non-stale tasks require justification before rerun.
- Preserve constraints override LLM choices.
- Retry counts prevent loops.
- Response node should not run if required work is incomplete.

Dependency invalidation should remain even with an LLM orchestrator. Stale statuses ground the LLM and reduce wrong subagent calls.

## Phase 5: Provider/MCP Service Layer

Goal: replace mocks behind clean interfaces.

Service modules should live outside the graph:

```text
app/services/flights/
app/services/accommodations/
app/services/search/
```

These can be:

- mock-backed
- REST/API-backed
- SDK-backed
- MCP-backed

Graph nodes should not care which implementation is used.

Example boundary:

```text
flight_node
-> FlightAgent or FlightService
-> MCP/API provider
-> normalized FlightOption list
```

Keep provider-specific code out of graph nodes.

## Phase 6: Specialist Subagents

Goal: turn simple graph nodes into bounded specialist agents where useful.

Strict terminology:

- A pure API/MCP call is better called a service/tool/provider adapter.
- A subagent usually implies some reasoning or autonomy, often LLM-backed.

Final pattern:

```text
orchestrator
-> bounded specialist subagent
-> subagent uses MCP tools / APIs
-> subagent returns structured results and quality metadata
-> orchestrator decides next workflow step
```

Recommended agentic candidates:

- `web_search_agent`: likely benefits from search refinement.
- `itinerary_agent`: benefits from planning and revision reasoning.
- `accommodation_agent`: may benefit from qualitative preferences.
- `flight_agent`: may be agentic later if multiple providers/flexible constraints exist.

Each subagent should return:

- structured results
- quality metadata
- assumptions
- errors
- retryable flag
- provider metadata

Use bounded ReAct loops only where useful:

- max iterations
- max tool calls
- clear stop conditions
- structured output required

Subagents reason locally. Orchestrator reasons globally.

## Phase 7: Ranking And Validation

Goal: make results trustworthy and explainable.

Ranking should stay mostly deterministic.

Current MVP flight ranking:

- Standard/default: lowest price first.
- Cheap: lowest price first.
- Luxurious: highest price first.
- Convenience is intentionally ignored for now.

Future ranking can consider:

Flights:

- price
- duration
- stops
- departure time
- arrival time
- baggage
- refundability
- airport preference
- layover duration

Accommodation:

- price
- rating
- location
- distance to transit
- amenities
- cancellation policy
- review count
- area preference

Recommended approach:

```text
LLM interprets soft preference
-> deterministic code converts preferences into weights/constraints
-> deterministic ranker scores options
-> response agent explains trade-offs
```

Validation should produce quality metadata:

```json
{
  "quality": {
    "flight": {
      "sufficient": false,
      "reason": "No flights found within budget.",
      "retryable": true,
      "suggested_next_step": "relax_budget_or_try_fallback"
    }
  }
}
```

The orchestrator reads quality metadata to decide retries, fallbacks, clarification, or partial response.

## Phase 8: Itinerary Generation And Revision

Goal: make the planner genuinely useful.

Support:

- new itinerary generation
- targeted day edits
- whole-itinerary edits
- preserve unaffected days
- preserve flights/accommodation when requested
- regenerate only affected parts where possible
- increment `itinerary_version`
- record assumptions and warnings
- validate arrival/departure timing
- validate activity pacing

Example targeted revision flow:

```text
User: "Day 2 is too packed. Remove the museum and add shopping."

Turn interpreter
-> changed_fields = ["itinerary_day_2", "activity_preferences"]

Dependency invalidation
-> itinerary = stale

Orchestrator
-> itinerary_agent

Itinerary agent
-> revises Day 2
-> preserves other days
-> returns complete updated itinerary

Orchestrator
-> response_agent
```

## Phase 9: Multi-Turn Persistence

Goal: preserve trip state across turns.

Use LangGraph checkpointers.

Development:

```python
InMemorySaver()
```

Production:

```text
SQLite or Postgres checkpointer
```

Every trip conversation should reuse the same `thread_id`:

```text
user-123-tokyo-trip
```

Different trips should use different thread IDs.

Tests:

- Create trip, then revise Day 2 using same `thread_id`.
- Previous itinerary is restored.
- Flight and accommodation are preserved during itinerary-only revision.
- Hotel change can mark itinerary stale without rerunning flight.

## Phase 10: FastAPI Streaming Contract

Goal: make the backend frontend-ready.

Potential endpoints:

```text
POST /api/travel/stream
POST /api/travel/invoke
GET /api/travel/{thread_id}/state
GET /health
```

Streaming should eventually emit stable event types:

```text
node_started
node_completed
subagent_started
subagent_completed
partial_result
clarification_required
final_response
error
```

The frontend should not depend on internal LangGraph implementation details. It should consume stable API/event contracts.

## Phase 11: Response Agent

Goal: produce polished user-facing responses from structured state.

Response agent should:

- present ranked flight options
- present ranked accommodation options
- present itinerary
- explain trade-offs
- mention assumptions
- mention warnings
- explain partial failures
- answer follow-up questions from existing state
- reformat existing results when requested

Response agent should not:

- call tools
- redo ranking
- invent prices
- invent availability
- silently regenerate itinerary
- make hidden provider calls

Presentation-only requests should route directly to response when no travel artifact needs regeneration.

Example:

```text
Show the same itinerary in a table.
```

Expected flow:

```text
turn_interpreter
-> dependency_invalidation marks nothing stale
-> orchestrator
-> response_agent
```

## Phase 12: Production Hardening

Goal: make the service deployable and maintainable.

Add:

- structured logging
- tracing
- request IDs
- timeout handling
- retry policies
- rate limiting
- config management
- secrets management
- durable checkpointer
- auth if needed
- Dockerfile
- CI checks
- deployment config
- provider error handling
- observability around subagent/tool calls

Production concerns:

- no unbounded ReAct loops
- no hidden booking/payment
- explicit user confirmation for any booking/payment action
- partial failure handling
- provider timeout fallback
- clear user-facing warnings for stale or unavailable data

## Recommended Short-Term Next Step

Start Phase 2.

Focus specifically on:

1. Finalizing `TravelState`.
2. Finalizing dependency invalidation rules.
3. Finalizing task status lifecycle.
4. Adding tests for stale status transitions.
5. Adding more routing tests.

Do not jump to real MCP/API providers yet. The graph control logic should be trustworthy first.
