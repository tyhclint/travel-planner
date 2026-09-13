from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.graph.nodes.itinerary_planner import itinerary_planner_node, route_itinerary_planner
from app.graph.state import TravelState


class FakeItineraryLLM:
    def __init__(self, responses: list[AIMessage]):
        self.responses = responses

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if not self.responses:
            raise AssertionError("No fake itinerary LLM responses remain.")
        return self.responses.pop(0)


def test_itinerary_react_loop_can_research_validate_and_finish(monkeypatch):
    research_calls: list[dict[str, Any]] = []
    validation_calls: list[dict[str, Any]] = []
    finish_calls: list[dict[str, Any]] = []

    @tool
    def destination_research_tool(
        destination: str,
        interests: list[str] | None = None,
        trip_length_days: int = 3,
        currency: str = "USD",
        pace: str = "balanced",
    ) -> dict[str, Any]:
        """Return fake destination research."""
        research_calls.append(
            {
                "destination": destination,
                "interests": interests or [],
                "trip_length_days": trip_length_days,
                "currency": currency,
                "pace": pace,
            }
        )
        return {
            "provider": "mock",
            "destination": destination,
            "recommendations": [
                {
                    "name": f"{destination} food market",
                    "category": "food",
                    "description": "A mock food stop.",
                    "source_url": "https://example.test/food",
                }
            ],
        }

    @tool
    def validate_day_plan(
        day: int,
        title: str,
        rationale: str,
        activities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return a fake validated itinerary day."""
        validation_calls.append(
            {
                "day": day,
                "title": title,
                "rationale": rationale,
                "activities": activities,
            }
        )
        return {
            "status": "validated",
            "day": {
                "day": day,
                "title": title,
                "rationale": rationale,
                "activities": activities,
            },
        }

    @tool
    def finish_itinerary_planning(reason: str) -> dict[str, str]:
        """Return a fake terminal itinerary-planning response."""
        finish_calls.append({"reason": reason})
        return {"status": "finished", "reason": reason}

    fake_llm = FakeItineraryLLM(
        [
            _research_call("call-research"),
            _validate_call("call-validate"),
            _finish_call("call-finish"),
        ]
    )
    monkeypatch.setattr("app.graph.nodes.itinerary_planner.get_itinerary_llm", lambda: fake_llm)

    graph = _build_test_graph(
        [destination_research_tool, validate_day_plan, finish_itinerary_planning]
    )

    result = graph.invoke(
        _state(),
        config={"configurable": {"thread_id": "test-itinerary-react-loop"}},
    )

    assert research_calls == [
        {
            "destination": "Tokyo",
            "interests": ["food"],
            "trip_length_days": 3,
            "currency": "USD",
            "pace": "balanced",
        }
    ]
    assert validation_calls[0]["day"] == 1
    assert finish_calls == [{"reason": "Enough validated itinerary days."}]
    assert result["task_status"]["itinerary"] == "completed"
    assert result["current_itinerary"].destination == "Tokyo"
    assert result["current_itinerary"].days[0].activities[0].title == "Tokyo food market"
    assert result["fan_in_notes"] == ["itinerary completed"]


def _build_test_graph(tools):
    builder = StateGraph(TravelState)

    builder.add_node("itinerary_planner_agent", itinerary_planner_node)
    builder.add_node("itinerary_tools", ToolNode(tools))
    builder.add_node("fan_in", lambda state: {"fan_in_notes": ["itinerary completed"]})

    builder.add_edge(START, "itinerary_planner_agent")
    builder.add_conditional_edges(
        "itinerary_planner_agent",
        route_itinerary_planner,
        {
            "itinerary_tools": "itinerary_tools",
            "fan_in": "fan_in",
        },
    )
    builder.add_edge("itinerary_tools", "itinerary_planner_agent")
    builder.add_edge("fan_in", END)

    return builder.compile()


def _state():
    return {
        "messages": [],
        "latest_user_input": "Plan a 3-day Tokyo food itinerary.",
        "trip_requirements": TripRequirements(
            destination="Tokyo",
            trip_length_days=3,
            travellers=1,
            currency="USD",
        ),
        "preferences": TravelPreferences(activity_pace="balanced", interests=["food"]),
        "task_status": {"itinerary": "pending"},
    }


def _research_call(call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "destination_research_tool",
                "args": {
                    "destination": "Tokyo",
                    "interests": ["food"],
                    "trip_length_days": 3,
                    "currency": "USD",
                    "pace": "balanced",
                },
                "id": call_id,
            }
        ],
    )


def _validate_call(call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "validate_day_plan",
                "args": {
                    "day": 1,
                    "title": "Day 1 in Tokyo",
                    "rationale": "Start with food and culture near the destination core.",
                    "activities": [
                        {
                            "time": "10:00",
                            "title": "Tokyo food market",
                            "description": "A mock food stop.",
                            "category": "food",
                            "location": "Tokyo",
                            "duration_minutes": 120,
                            "url": "https://example.test/food",
                        }
                    ],
                },
                "id": call_id,
            }
        ],
    )


def _finish_call(call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "finish_itinerary_planning",
                "args": {"reason": "Enough validated itinerary days."},
                "id": call_id,
            }
        ],
    )
