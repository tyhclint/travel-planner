from langchain_core.messages import HumanMessage

from app.graph.builder import build_graph


class FakeTurnInterpreterLLM:
    def __init__(self, output):
        self.output = output

    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return self.output


class FakeOrchestratorLLM:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        if not self.outputs:
            raise AssertionError("No fake orchestrator decisions remain.")

        return self.outputs.pop(0)


def _mock_turn_interpreter(monkeypatch, output):
    monkeypatch.setattr(
        "app.graph.nodes.turn_interpreter.get_turn_interpreter_llm",
        lambda: FakeTurnInterpreterLLM(output),
    )


def _mock_orchestrator(monkeypatch, outputs):
    fake_llm = FakeOrchestratorLLM(outputs)
    monkeypatch.setattr(
        "app.services.orchestration.llm.get_orchestrator_llm",
        lambda: fake_llm,
    )


def test_graph_builds_mock_trip_response(monkeypatch):
    _mock_turn_interpreter(
        monkeypatch,
        {
            "turn_type": "new_plan",
            "intent_summary": "User wants a cheap 5-day trip from Singapore to Tokyo.",
            "requested_capabilities": [
                "flight",
                "accommodation",
                "destination_research",
                "itinerary",
            ],
            "trip_requirement_updates": {
                "origin": "Singapore",
                "destination": "Tokyo",
                "trip_length_days": 5,
            },
            "preference_updates": {
                "overall_style": "cheap",
                "flight_style": "cheap",
                "accommodation_style": "cheap",
                "flight_priority": "cheapest",
                "accommodation_priority": "cheapest",
            },
            "changed_fields": [
                "origin",
                "destination",
                "travel_dates",
                "budget",
                "flight_preferences",
                "accommodation_preferences",
            ],
        }
    )
    _mock_orchestrator(
        monkeypatch,
        [
            {
                "next_tasks": [
                    "flight_agent",
                    "accommodation_agent",
                    "destination_research_agent",
                ],
                "reason": "Independent search tasks can run together.",
            },
            {
                "next_tasks": ["itinerary_planner_agent"],
                "reason": "Itinerary work is pending after upstream tasks completed.",
            },
            {
                "next_tasks": ["response_agent"],
                "can_answer_now": True,
                "reason": "All requested planning work is complete.",
            },
        ],
    )
    graph = build_graph()

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="Plan me a cheap 5-day trip from Singapore to Tokyo")
            ],
            "latest_user_input": "Plan me a cheap 5-day trip from Singapore to Tokyo",
        },
        config={"configurable": {"thread_id": "test-trip"}},
    )

    assert result["task_status"]["flight"] == "completed"
    assert result["task_status"]["accommodation"] == "completed"
    assert result["task_status"]["ranking"] == "completed"
    assert result["task_status"]["destination_research"] == "completed"
    assert result["task_status"]["itinerary"] == "completed"
    assert "Top flight" in result["final_response"]
    assert "Itinerary" in result["final_response"]


def test_graph_routes_flight_only_request_without_accommodation(monkeypatch):
    _mock_turn_interpreter(
        monkeypatch,
        {
            "turn_type": "new_plan",
            "intent_summary": "User wants flights from Singapore to Tokyo.",
            "requested_capabilities": ["flight"],
            "trip_requirement_updates": {
                "origin": "Singapore",
                "destination": "Tokyo",
            },
            "changed_fields": ["origin", "destination"],
        }
    )
    _mock_orchestrator(
        monkeypatch,
        [
            {
                "next_tasks": ["flight_agent"],
                "reason": "Flight work is pending.",
            },
            {
                "next_tasks": ["response_agent"],
                "can_answer_now": True,
                "reason": "The requested flight search is complete.",
            },
        ],
    )
    graph = build_graph()

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="Find flights from Singapore to Tokyo")],
            "latest_user_input": "Find flights from Singapore to Tokyo",
        },
        config={"configurable": {"thread_id": "test-flight-only"}},
    )

    assert result["task_status"]["flight"] == "completed"
    assert result["task_status"]["accommodation"] == "not_required"
    assert result["task_status"]["ranking"] == "completed"
    assert result["task_status"]["itinerary"] == "not_required"
    assert "Top flight" in result["final_response"]
    assert "Top stay" not in result["final_response"]


def test_graph_routes_accommodation_only_request_without_flight(monkeypatch):
    _mock_turn_interpreter(
        monkeypatch,
        {
            "turn_type": "new_plan",
            "intent_summary": "User wants accommodation in Tokyo.",
            "requested_capabilities": ["accommodation"],
            "trip_requirement_updates": {
                "destination": "Tokyo",
            },
            "changed_fields": ["destination"],
        }
    )
    _mock_orchestrator(
        monkeypatch,
        [
            {
                "next_tasks": ["accommodation_agent"],
                "reason": "Accommodation work is pending.",
            },
            {
                "next_tasks": ["response_agent"],
                "can_answer_now": True,
                "reason": "The requested accommodation search is complete.",
            },
        ],
    )
    graph = build_graph()

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="Find a hotel in Tokyo")],
            "latest_user_input": "Find a hotel in Tokyo",
        },
        config={"configurable": {"thread_id": "test-accommodation-only"}},
    )

    assert result["task_status"]["accommodation"] == "completed"
    assert result["task_status"]["flight"] == "not_required"
    assert result["task_status"]["ranking"] == "completed"
    assert result["task_status"]["itinerary"] == "not_required"
    assert "Top stay" in result["final_response"]
    assert "Top flight" not in result["final_response"]
