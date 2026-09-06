import json

from langchain_core.messages import AIMessage, ToolMessage

from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.graph.nodes.flight import flight_node, route_flight_agent


class FakeFlightLLM:
    def __init__(self, response):
        self.response = response

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return self.response


def test_flight_node_returns_tool_action_without_results(monkeypatch):
    response = _search_call()
    monkeypatch.setattr("app.graph.nodes.flight.get_flight_llm", lambda: FakeFlightLLM(response))

    result = flight_node(_state())

    assert result["messages"] == [response]
    assert result["task_status"] == {"flight": "running"}
    assert "flight_results" not in result


def test_route_flight_agent_sends_known_tool_calls_to_tool_node():
    route = route_flight_agent({"messages": [_search_call()]})

    assert route == "flight_tools"


def test_flight_node_populates_results_after_finish_tool_message():
    result = flight_node(
        _state(
            messages=[
                _search_call(),
                ToolMessage(
                    content=json.dumps(
                        {
                            "provider": "kiwi",
                            "result": {
                                "query": "Singapore to Tokyo",
                                "currency": "USD",
                                "resultsCount": 1,
                                "itineraries": [
                                    {
                                        "id": "kiwi-1",
                                        "price": 320,
                                        "priceFormatted": "320 USD",
                                        "totalDurationSeconds": 25200,
                                        "bookingUrl": "https://example.test/booking",
                                        "baggage": {
                                            "personalItem": 1,
                                            "cabinBag": 1,
                                            "checkedBag": 0,
                                        },
                                        "outbound": {
                                            "from": "SIN",
                                            "to": "NRT",
                                            "departureTime": "2026-10-01T08:00:00+00:00",
                                            "arrivalTime": "2026-10-01T15:00:00+00:00",
                                            "durationSeconds": 25200,
                                            "stops": 0,
                                            "route": ["SIN", "NRT"],
                                            "cabinClass": "Economy",
                                            "segments": [
                                                {
                                                    "from": "SIN",
                                                    "to": "NRT",
                                                    "carrier": "TR",
                                                    "carrierName": "Scoot",
                                                    "flightNumber": "TR808",
                                                    "cabinClass": "Economy",
                                                }
                                            ],
                                        },
                                    }
                                ],
                                "searchTimeMs": 123,
                            },
                        }
                    ),
                    name="search_flights",
                    tool_call_id="call-search",
                ),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "finish_flight_search",
                            "args": {"reason": "Enough usable options."},
                            "id": "call-finish",
                        }
                    ],
                ),
                ToolMessage(
                    content=json.dumps({"status": "finished"}),
                    name="finish_flight_search",
                    tool_call_id="call-finish",
                ),
            ]
        )
    )

    assert result["task_status"] == {"flight": "completed"}
    assert len(result["flight_results"]) == 1
    assert result["flight_results"][0].id == "kiwi-1"
    assert result["flight_results"][0].airline == "Scoot"
    assert result["flight_results"][0].duration_minutes == 420
    assert result["flight_results"][0].provider == "kiwi"


def test_flight_node_rejects_plain_text_llm_output(monkeypatch):
    response = AIMessage(content="I found enough flights.")
    monkeypatch.setattr("app.graph.nodes.flight.get_flight_llm", lambda: FakeFlightLLM(response))

    result = flight_node(_state())

    assert result["messages"] == [response]
    assert result["task_status"] == {"flight": "failed"}
    assert result["errors"][0].error_type == "invalid_llm_action"


def _state(messages=None):
    return {
        "messages": messages or [],
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


def _search_call():
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_flights",
                "args": {
                    "fly_from": "SIN",
                    "fly_to": "TYO",
                    "departure_date": "2026-10-01",
                    "adults": 1,
                    "cabin_class": "economy",
                    "currency": "USD",
                    "sort": "price",
                },
                "id": "call-search",
            }
        ],
    )
