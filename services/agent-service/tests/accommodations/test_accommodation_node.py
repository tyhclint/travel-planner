import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.domain.models.errors import AccommodationError
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.graph.nodes.accommodation import accommodation_node, route_accommodation_agent


class FakeAccommodationLLM:
    def __init__(self, response):
        self.response = response

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return self.response


class FailingAccommodationLLM:
    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        raise RuntimeError("provider unavailable")


def test_accommodation_node_returns_tool_action_without_results(monkeypatch):
    response = _search_call()
    monkeypatch.setattr(
        "app.graph.nodes.accommodation.get_accommodation_llm",
        lambda: FakeAccommodationLLM(response),
    )

    result = accommodation_node(_state())

    assert result["messages"] == [response]
    assert result["task_status"] == {"accommodation": "running"}
    assert "accommodation_results" not in result


def test_route_accommodation_agent_sends_known_tool_calls_to_tool_node():
    route = route_accommodation_agent({"messages": [_search_call()]})

    assert route == "accommodation_tools"


def test_accommodation_node_populates_results_after_finish_tool_message():
    result = accommodation_node(
        _state(
            messages=[
                _search_call(),
                ToolMessage(
                    content=json.dumps(
                        {
                            "provider": "moodtrip",
                            "tool": "searchHotelsWithRates",
                            "result": {
                                "checkIn": "2026-10-01",
                                "checkOut": "2026-10-05",
                                "currency": "USD",
                                "hotels": [
                                    {
                                        "id": "hotel-1",
                                        "name": "Tokyo Central Hotel",
                                        "city": "Tokyo",
                                        "rating": 4.4,
                                        "price": {
                                            "nightly": 150,
                                            "total": 600,
                                            "currency": "USD",
                                        },
                                    }
                                ],
                            },
                        }
                    ),
                    name="search_accommodations",
                    tool_call_id="call-search",
                ),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "finish_accommodation_search",
                            "args": {"reason": "Enough usable options."},
                            "id": "call-finish",
                        }
                    ],
                ),
                ToolMessage(
                    content=json.dumps({"status": "finished"}),
                    name="finish_accommodation_search",
                    tool_call_id="call-finish",
                ),
            ]
        )
    )

    assert result["task_status"] == {"accommodation": "completed"}
    assert len(result["accommodation_results"]) == 1
    assert result["accommodation_results"][0].id == "hotel-1"
    assert result["accommodation_results"][0].name == "Tokyo Central Hotel"
    assert result["accommodation_results"][0].provider == "moodtrip"


def test_accommodation_node_raises_plain_text_llm_output_in_debug_mode(monkeypatch):
    response = AIMessage(content="I found enough hotels.")
    monkeypatch.setattr(
        "app.graph.nodes.accommodation.get_accommodation_llm",
        lambda: FakeAccommodationLLM(response),
    )

    with pytest.raises(AccommodationError, match="exactly one accommodation tool"):
        accommodation_node(_state())


def test_accommodation_node_records_plain_text_llm_output_in_production_mode(monkeypatch):
    response = AIMessage(content="I found enough hotels.")
    monkeypatch.setattr(
        "app.graph.nodes.accommodation.get_accommodation_llm",
        lambda: FakeAccommodationLLM(response),
    )
    monkeypatch.setattr("app.graph.nodes.accommodation.settings.debug", False)

    result = accommodation_node(_state())

    assert result["messages"] == [response]
    assert result["task_status"] == {"accommodation": "failed"}
    assert result["errors"][0].error_type == "invalid_llm_action"


def test_accommodation_node_records_llm_failure_in_production_mode(monkeypatch):
    monkeypatch.setattr(
        "app.graph.nodes.accommodation.get_accommodation_llm",
        lambda: FailingAccommodationLLM(),
    )
    monkeypatch.setattr("app.graph.nodes.accommodation.settings.debug", False)

    result = accommodation_node(_state())

    assert result["task_status"] == {"accommodation": "failed"}
    assert result["errors"][0].error_type == "llm_action_failed"
    assert "provider unavailable" in result["errors"][0].message


def _state(messages=None):
    return {
        "messages": messages or [],
        "latest_user_input": "Find hotels in Tokyo.",
        "trip_requirements": TripRequirements(
            destination="Tokyo",
            departure_date="2026-10-01",
            return_date="2026-10-05",
            travellers=2,
            currency="USD",
        ),
        "preferences": TravelPreferences(accommodation_priority="best_location"),
        "task_status": {"accommodation": "pending"},
    }


def _search_call():
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_accommodations",
                "args": {
                    "city_name": "Tokyo",
                    "country_code": "JP",
                    "checkin": "2026-10-01",
                    "checkout": "2026-10-05",
                    "occupancies": [{"adults": 2, "children": []}],
                    "currency": "USD",
                },
                "id": "call-search",
            }
        ],
    )
