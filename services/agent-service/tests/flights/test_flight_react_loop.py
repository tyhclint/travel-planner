from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.graph.nodes.flight import flight_node, route_flight_agent
from app.graph.state import TravelState


class FakeFlightLLM:
    def __init__(self, responses: list[AIMessage]):
        self.responses = responses

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if not self.responses:
            raise AssertionError("No fake flight LLM responses remain.")
        return self.responses.pop(0)


def test_flight_react_loop_can_call_tool_node_twice_before_finishing(monkeypatch):
    search_calls: list[dict[str, Any]] = []
    finish_calls: list[dict[str, Any]] = []

    @tool
    def search_flights(
        fly_from: str,
        fly_to: str,
        departure_date: str,
        currency: str = "USD",
        sort: str = "price",
    ) -> dict[str, Any]:
        """Return a fake Kiwi-shaped flight search response."""
        search_calls.append(
            {
                "fly_from": fly_from,
                "fly_to": fly_to,
                "departure_date": departure_date,
                "currency": currency,
                "sort": sort,
            }
        )
        search_number = len(search_calls)
        return _kiwi_search_result(search_number, currency)

    @tool
    def finish_flight_search(reason: str) -> dict[str, str]:
        """Return a fake terminal flight-search response."""
        finish_calls.append({"reason": reason})
        return {"status": "finished", "reason": reason}

    fake_llm = FakeFlightLLM(
        [
            _search_call("call-search-1", sort="price"),
            _search_call("call-search-2", sort="duration"),
            _finish_call("call-finish"),
        ]
    )
    monkeypatch.setattr("app.graph.nodes.flight.get_flight_llm", lambda: fake_llm)

    graph = _build_test_graph([search_flights, finish_flight_search])

    result = graph.invoke(
        _state(),
        config={"configurable": {"thread_id": "test-flight-react-loop"}},
    )

    assert len(search_calls) == 2
    assert search_calls[0]["sort"] == "price"
    assert search_calls[1]["sort"] == "duration"
    assert finish_calls == [{"reason": "Enough usable flight options."}]
    assert result["task_status"]["flight"] == "completed"
    assert len(result["flight_results"]) == 2
    assert {option.id for option in result["flight_results"]} == {"kiwi-1", "kiwi-2"}
    assert result["fan_in_notes"] == ["flight completed"]


def _build_test_graph(tools):
    builder = StateGraph(TravelState)

    builder.add_node("flight_agent", flight_node)
    builder.add_node("flight_tools", ToolNode(tools))
    builder.add_node("fan_in", lambda state: {"fan_in_notes": ["flight completed"]})

    builder.add_edge(START, "flight_agent")
    builder.add_conditional_edges(
        "flight_agent",
        route_flight_agent,
        {
            "flight_tools": "flight_tools",
            "fan_in": "fan_in",
        },
    )
    builder.add_edge("flight_tools", "flight_agent")
    builder.add_edge("fan_in", END)

    return builder.compile()


def _state():
    return {
        "messages": [],
        "latest_user_input": "Find flights from Singapore to Tokyo.",
        "trip_requirements": TripRequirements(
            origin="Singapore",
            destination="Tokyo",
            departure_date="2026-10-01",
            travellers=1,
            currency="USD",
        ),
        "preferences": TravelPreferences(flight_priority="cheapest"),
        "task_status": {"flight": "pending"},
    }


def _search_call(call_id: str, *, sort: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_flights",
                "args": {
                    "fly_from": "SIN",
                    "fly_to": "TYO",
                    "departure_date": "2026-10-01",
                    "currency": "USD",
                    "sort": sort,
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
                "name": "finish_flight_search",
                "args": {"reason": "Enough usable flight options."},
                "id": call_id,
            }
        ],
    )


def _kiwi_search_result(search_number: int, currency: str) -> dict[str, Any]:
    departure_hour = 7 + search_number
    arrival_hour = departure_hour + 7
    return {
        "provider": "kiwi",
        "result": {
            "query": "Singapore to Tokyo",
            "currency": currency,
            "resultsCount": 1,
            "itineraries": [
                {
                    "id": f"kiwi-{search_number}",
                    "price": 300 + search_number,
                    "totalDurationSeconds": 25200,
                    "bookingUrl": f"https://example.test/booking/{search_number}",
                    "outbound": {
                        "from": "SIN",
                        "to": "NRT",
                        "departureTime": f"2026-10-01T{departure_hour:02d}:00:00+00:00",
                        "arrivalTime": f"2026-10-01T{arrival_hour:02d}:00:00+00:00",
                        "durationSeconds": 25200,
                        "stops": 0,
                        "route": ["SIN", "NRT"],
                        "cabinClass": "Economy",
                        "segments": [
                            {
                                "carrier": "TR",
                                "carrierName": "Scoot",
                            }
                        ],
                    },
                }
            ],
            "searchTimeMs": 10,
        },
    }
