import pytest
from langchain_core.messages import HumanMessage

from app.domain.models.errors import TurnInterpreterError
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.domain.models.turn_interpreter import TurnInterpreterOutput
from app.graph.nodes.turn_interpreter import turn_interpreter_node


class RecordingTurnInterpreterLLM:
    def __init__(self, output):
        self.output = output
        self.structured_output_schema = None
        self.invoked_messages = None

    def with_structured_output(self, schema):
        self.structured_output_schema = schema
        return self

    def invoke(self, messages):
        self.invoked_messages = messages
        return self.output


def _mock_turn_interpreter_llm(monkeypatch, output):
    llm = RecordingTurnInterpreterLLM(output)
    monkeypatch.setattr(
        "app.graph.nodes.turn_interpreter.get_turn_interpreter_llm",
        lambda: llm,
    )
    return llm


def test_turn_interpreter_uses_structured_output_and_merges_updates(monkeypatch):
    """ Deterministic tests for turn_interpreter node"""

    llm = _mock_turn_interpreter_llm(
        monkeypatch,
        {
            "turn_type": "revision",
            "intent_summary": "User wants a nicer hotel while keeping flights unchanged.",
            "requested_capabilities": ["accommodation", "accommodation", "itinerary"],
            "trip_requirement_updates": {
                "destination": "Tokyo",
                "travellers": 2,
            },
            "preference_updates": {
                "accommodation_style": "luxurious",
                "activity_pace": "packed",
                "interests": ["food", "shopping"],
            },
            "constraints": {
                "preserve_flights": True,
                "preserve_unaffected_itinerary_days": True,
            },
            "changed_fields": [
                "destination",
                "destination",
                "accommodation_preferences",
            ],
            "revision_targets": [
                {
                    "artifact": "itinerary",
                    "scope": "day",
                    "day": 2,
                }
            ],
            "latest_feedback": {
                "add": ["shopping"],
                "preserve": ["flights"],
                "instruction": "Upgrade the hotel and preserve the flights.",
            },
            "missing_required_fields": ["budget", "budget"],
        },
    )
    requirements = TripRequirements(origin="Singapore", currency="SGD")
    preferences = TravelPreferences(overall_style="cheap", flight_priority="cheapest")

    result = turn_interpreter_node(
        {
            "latest_user_input": "Make the hotel nicer, keep the flights, add shopping.",
            "trip_requirements": requirements,
            "preferences": preferences,
        }
    )

    assert llm.structured_output_schema is TurnInterpreterOutput
    assert llm.invoked_messages[-1].content.endswith(
        "Interpret the latest user input and return structured output.\n"
    )

    assert result["latest_user_input"] == (
        "Make the hotel nicer, keep the flights, add shopping."
    )
    assert result["turn_type"] == "revision"
    assert result["requested_capabilities"] == ["accommodation", "itinerary"]
    assert result["trip_requirement_updates"] == {
        "destination": "Tokyo",
        "travellers": 2,
    }
    assert result["preference_updates"] == {
        "accommodation_style": "luxurious",
        "activity_pace": "packed",
        "interests": ["food", "shopping"],
    }
    assert result["constraints"] == {
        "preserve_flights": True,
        "preserve_unaffected_itinerary_days": True,
    }
    assert result["trip_requirements"].origin == "Singapore"
    assert result["trip_requirements"].destination == "Tokyo"
    assert result["trip_requirements"].travellers == 2
    assert result["trip_requirements"].currency == "SGD"
    assert result["preferences"].overall_style == "cheap"
    assert result["preferences"].flight_priority == "cheapest"
    assert result["preferences"].accommodation_style == "luxurious"
    assert result["preferences"].activity_pace == "packed"
    assert result["preferences"].interests == ["food", "shopping"]
    assert result["changed_fields"] == ["destination", "accommodation_preferences"]
    assert result["revision_targets"] == [
        {
            "artifact": "itinerary",
            "scope": "day",
            "day": 2,
        }
    ]
    assert result["latest_feedback"] == {
        "add": ["shopping"],
        "preserve": ["flights"],
        "instruction": "Upgrade the hotel and preserve the flights.",
    }
    assert result["missing_required_fields"] == ["budget"]


def test_turn_interpreter_preserves_existing_defaults_when_no_updates(monkeypatch):
    _mock_turn_interpreter_llm(
        monkeypatch,
        {
            "turn_type": "follow_up_question",
            "intent_summary": "User asks about the existing plan.",
            "requested_capabilities": [],
        },
    )
    requirements = TripRequirements(origin="Singapore", destination="Tokyo")
    preferences = TravelPreferences(overall_style="cheap")

    result = turn_interpreter_node(
        {
            "latest_user_input": "What is the best option?",
            "trip_requirements": requirements,
            "preferences": preferences,
        }
    )

    assert result["trip_requirement_updates"] == {}
    assert result["preference_updates"] == {}
    assert result["constraints"] == {}
    assert result["trip_requirements"] == requirements
    assert result["preferences"] == preferences
    assert result["changed_fields"] == []
    assert result["revision_targets"] == []
    assert result["latest_feedback"] == {}
    assert result["missing_required_fields"] == []


def test_turn_interpreter_uses_latest_human_message_when_input_is_missing(monkeypatch):
    _mock_turn_interpreter_llm(
        monkeypatch,
        {
            "turn_type": "new_plan",
            "intent_summary": "User wants flights to Tokyo.",
            "requested_capabilities": ["flight"],
            "trip_requirement_updates": {
                "destination": "Tokyo",
            },
        },
    )

    result = turn_interpreter_node(
        {
            "messages": [HumanMessage(content="Find flights to Tokyo")],
        }
    )

    assert result["latest_user_input"] == "Find flights to Tokyo"
    assert result["trip_requirements"].destination == "Tokyo"


def test_turn_interpreter_wraps_invalid_llm_output(monkeypatch):
    _mock_turn_interpreter_llm(
        monkeypatch,
        {
            "turn_type": "new_plan",
        },
    )

    with pytest.raises(TurnInterpreterError):
        turn_interpreter_node({"latest_user_input": "Plan a trip"})
