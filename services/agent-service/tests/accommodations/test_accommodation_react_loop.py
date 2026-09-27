from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.graph.nodes.accommodation import accommodation_node, route_accommodation_agent
from app.graph.state import TravelState


class FakeAccommodationLLM:
    def __init__(self, responses: list[AIMessage]):
        self.responses = responses

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if not self.responses:
            raise AssertionError("No fake accommodation LLM responses remain.")
        return self.responses.pop(0)


def test_accommodation_react_loop_can_search_review_and_finish(monkeypatch):
    search_calls: list[dict[str, Any]] = []
    review_calls: list[dict[str, Any]] = []
    finish_calls: list[dict[str, Any]] = []

    @tool
    def search_accommodations(
        destination: str,
        check_in: str,
        check_out: str,
        adults: int = 1,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Return a fake MoodTrip-shaped hotel search response."""
        search_calls.append(
            {
                "destination": destination,
                "check_in": check_in,
                "check_out": check_out,
                "adults": adults,
                "currency": currency,
            }
        )
        return _moodtrip_search_result(currency)

    @tool
    def get_accommodation_reviews(hotel_id: str, limit: int = 10) -> dict[str, Any]:
        """Return a fake MoodTrip-shaped hotel review response."""
        review_calls.append({"hotel_id": hotel_id, "limit": limit})
        return {
            "provider": "moodtrip",
            "tool": "getHotelReviews",
            "hotel_id": hotel_id,
            "result": {
                "summary": "Excellent access to rail stations.",
                "averageRating": 4.6,
            },
        }

    @tool
    def finish_accommodation_search(reason: str) -> dict[str, str]:
        """Return a fake terminal accommodation-search response."""
        finish_calls.append({"reason": reason})
        return {"status": "finished", "reason": reason}

    fake_llm = FakeAccommodationLLM(
        [
            _search_call("call-search"),
            _review_call("call-review"),
            _finish_call("call-finish"),
        ]
    )
    monkeypatch.setattr("app.graph.nodes.accommodation.get_accommodation_llm", lambda: fake_llm)

    graph = _build_test_graph(
        [search_accommodations, get_accommodation_reviews, finish_accommodation_search]
    )

    result = graph.invoke(
        _state(),
        config={"configurable": {"thread_id": "test-accommodation-react-loop"}},
    )

    assert search_calls == [
        {
            "destination": "Tokyo",
            "check_in": "2026-10-01",
            "check_out": "2026-10-05",
            "adults": 2,
            "currency": "USD",
        }
    ]
    assert review_calls == [{"hotel_id": "hotel-1", "limit": 5}]
    assert finish_calls == [{"reason": "Enough usable accommodation options."}]
    assert result["task_status"]["accommodation"] == "completed"
    assert len(result["accommodation_results"]) == 1
    assert result["accommodation_results"][0].id == "hotel-1"
    assert result["fan_in_notes"] == ["accommodation completed"]


def _build_test_graph(tools):
    builder = StateGraph(TravelState)

    builder.add_node("accommodation_agent", accommodation_node)
    builder.add_node("accommodation_tools", ToolNode(tools))
    builder.add_node("fan_in", lambda state: {"fan_in_notes": ["accommodation completed"]})

    builder.add_edge(START, "accommodation_agent")
    builder.add_conditional_edges(
        "accommodation_agent",
        route_accommodation_agent,
        {
            "accommodation_tools": "accommodation_tools",
            "fan_in": "fan_in",
        },
    )
    builder.add_edge("accommodation_tools", "accommodation_agent")
    builder.add_edge("fan_in", END)

    return builder.compile()


def _state():
    return {
        "messages": [],
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


def _search_call(call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_accommodations",
                "args": {
                    "destination": "Tokyo",
                    "check_in": "2026-10-01",
                    "check_out": "2026-10-05",
                    "adults": 2,
                    "currency": "USD",
                },
                "id": call_id,
            }
        ],
    )


def _review_call(call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_accommodation_reviews",
                "args": {
                    "hotel_id": "hotel-1",
                    "limit": 5,
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
                "name": "finish_accommodation_search",
                "args": {"reason": "Enough usable accommodation options."},
                "id": call_id,
            }
        ],
    )


def _moodtrip_search_result(currency: str) -> dict[str, Any]:
    return {
        "provider": "moodtrip",
        "tool": "searchHotelsWithRates",
        "result": {
            "checkIn": "2026-10-01",
            "checkOut": "2026-10-05",
            "currency": currency,
            "hotels": [
                {
                    "id": "hotel-1",
                    "name": "Tokyo Central Hotel",
                    "city": "Tokyo",
                    "rating": 4.4,
                    "price": {
                        "nightly": 150,
                        "total": 600,
                        "currency": currency,
                    },
                }
            ],
        },
    }
