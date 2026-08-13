from langchain_core.messages import HumanMessage

from app.graph.builder import build_graph


def test_graph_builds_mock_trip_response():
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


def test_graph_routes_flight_only_request_without_accommodation():
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


def test_graph_routes_accommodation_only_request_without_flight():
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
