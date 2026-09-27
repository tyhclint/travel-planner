import json

from langchain_core.messages import AIMessage, ToolMessage

from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.graph.nodes.itinerary_planner import itinerary_planner_node, route_itinerary_planner


class FakeItineraryLLM:
    def __init__(self, response):
        self.response = response

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return self.response


def test_itinerary_node_returns_tool_action_without_itinerary(monkeypatch):
    response = _research_call()
    monkeypatch.setattr(
        "app.graph.nodes.itinerary_planner.get_itinerary_llm",
        lambda: FakeItineraryLLM(response),
    )

    result = itinerary_planner_node(_state())

    assert result["messages"] == [response]
    assert result["task_status"] == {"itinerary": "running"}
    assert "current_itinerary" not in result


def test_route_itinerary_planner_sends_known_tool_calls_to_tool_node():
    route = route_itinerary_planner({"messages": [_research_call()]})

    assert route == "itinerary_tools"


def test_itinerary_node_populates_itinerary_after_finish_tool_message():
    result = itinerary_planner_node(
        _state(
            messages=[
                _research_call(),
                ToolMessage(
                    content=json.dumps(
                        {
                            "provider": "mock",
                            "destination": "Tokyo",
                            "recommendations": [
                                {
                                    "name": "Tokyo old town walk",
                                    "category": "culture",
                                    "description": "A mock cultural route.",
                                    "source_url": "https://example.test/research",
                                }
                            ],
                        }
                    ),
                    name="destination_research_tool",
                    tool_call_id="call-research",
                ),
                _validate_call(),
                ToolMessage(
                    content=json.dumps(
                        {
                            "status": "validated",
                            "day": {
                                "day": 1,
                                "title": "Day 1 in Tokyo",
                                "rationale": "Keep the first day easy and central.",
                                "activities": [
                                    {
                                        "time": "09:30",
                                        "title": "Tokyo old town walk",
                                        "description": "A mock cultural route.",
                                        "category": "culture",
                                        "location": "Tokyo",
                                        "duration_minutes": 150,
                                        "url": "https://example.test/activity",
                                    }
                                ],
                            },
                        }
                    ),
                    name="validate_day_plan",
                    tool_call_id="call-validate",
                ),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "finish_itinerary_planning",
                            "args": {"reason": "Enough validated days."},
                            "id": "call-finish",
                        }
                    ],
                ),
                ToolMessage(
                    content=json.dumps({"status": "finished"}),
                    name="finish_itinerary_planning",
                    tool_call_id="call-finish",
                ),
            ]
        )
    )

    assert result["task_status"] == {"itinerary": "completed"}
    assert result["current_itinerary"].destination == "Tokyo"
    assert result["current_itinerary"].days[0].day == 1
    assert result["current_itinerary"].days[0].activities[0].title == "Tokyo old town walk"
    assert result["destination_research_results"][0].name == "Tokyo old town walk"
    assert result["itinerary_version"] == 1


def test_itinerary_node_rejects_plain_text_llm_output(monkeypatch):
    response = AIMessage(content="I made an itinerary.")
    monkeypatch.setattr(
        "app.graph.nodes.itinerary_planner.get_itinerary_llm",
        lambda: FakeItineraryLLM(response),
    )

    result = itinerary_planner_node(_state())

    assert result["messages"] == [response]
    assert result["task_status"] == {"itinerary": "failed"}
    assert result["errors"][0].error_type == "invalid_llm_action"


def _state(messages=None):
    return {
        "messages": messages or [],
        "latest_user_input": "Plan a 3-day Tokyo itinerary.",
        "trip_requirements": TripRequirements(
            destination="Tokyo",
            trip_length_days=3,
            travellers=1,
            currency="USD",
        ),
        "preferences": TravelPreferences(activity_pace="balanced", interests=["food"]),
        "task_status": {"itinerary": "pending"},
    }


def _research_call():
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
                "id": "call-research",
            }
        ],
    )


def _validate_call():
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "validate_day_plan",
                "args": {
                    "day": 1,
                    "title": "Day 1 in Tokyo",
                    "rationale": "Keep the first day easy and central.",
                    "activities": [
                        {
                            "time": "09:30",
                            "title": "Tokyo old town walk",
                            "description": "A mock cultural route.",
                            "category": "culture",
                            "location": "Tokyo",
                            "duration_minutes": 150,
                            "url": "https://example.test/activity",
                        }
                    ],
                },
                "id": "call-validate",
            }
        ],
    )
