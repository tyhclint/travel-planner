import pytest

from app.domain.models.errors import OrchestratorError
from app.domain.models.orchestrator import OrchestratorDecision
from app.domain.orchestration.policy import MAX_ORCHESTRATION_STEPS
from app.graph.nodes.orchestrator import orchestrator_node, route_orchestrator


def test_route_orchestrator_routes_single_task_decision():
    decision = OrchestratorDecision(
        next_tasks=["flight_agent"],
        reason="Flight work is pending.",
    )

    route = route_orchestrator({"orchestrator_decision": decision.model_dump()})

    assert route == "flight_agent"


def test_route_orchestrator_routes_parallel_task_decision():
    decision = OrchestratorDecision(
        next_tasks=["flight_agent", "accommodation_agent"],
        reason="Independent search tasks can run together.",
    )

    route = route_orchestrator({"orchestrator_decision": decision.model_dump()})

    assert route == ["flight_agent", "accommodation_agent"]


def test_route_orchestrator_max_steps_overrides_stored_decision():
    decision = OrchestratorDecision(
        next_tasks=["flight_agent"],
        reason="Flight work is pending.",
    )

    route = route_orchestrator(
        {
            "orchestration_steps": MAX_ORCHESTRATION_STEPS,
            "orchestrator_decision": decision.model_dump(),
        }
    )

    assert route == "response_agent"


def test_route_orchestrator_missing_fields_override_stored_decision():
    decision = OrchestratorDecision(
        next_tasks=["response_agent"],
        can_answer_now=True,
        reason="The stored decision says the answer is ready.",
    )

    route = route_orchestrator(
        {
            "missing_required_fields": ["destination"],
            "orchestrator_decision": decision.model_dump(),
        }
    )

    assert route == "user_clarification"


def test_route_orchestrator_falls_back_when_stored_decision_is_invalid():
    route = route_orchestrator(
        {
            "orchestration_steps": 1,
            "task_status": {"flight": "pending"},
            "orchestrator_decision": {"next_tasks": [], "reason": ""},
        }
    )

    assert route == "flight_agent"


def test_orchestrator_node_uses_guardrail_without_calling_llm(monkeypatch):
    def fail_if_called(state, orchestration_steps):
        raise AssertionError("LLM should not be called when a guardrail applies.")

    monkeypatch.setattr(
        "app.graph.nodes.orchestrator.validated_llm_decision",
        fail_if_called,
    )

    result = orchestrator_node(
        {
            "missing_required_fields": ["budget"],
        }
    )

    assert result["orchestration_steps"] == 1
    assert result["orchestrator_decision"]["next_tasks"] == ["user_clarification"]
    assert result["orchestrator_decision"]["clarification_fields"] == ["budget"]


def test_orchestrator_node_applies_policy_to_llm_decision(monkeypatch):
    calls = []

    def llm_decision(state, orchestration_steps):
        calls.append((state, orchestration_steps))
        return OrchestratorDecision(
            next_tasks=["response_agent"],
            can_answer_now=True,
            reason="The LLM says the answer is ready.",
        )

    monkeypatch.setattr(
        "app.graph.nodes.orchestrator.validated_llm_decision",
        llm_decision,
    )

    result = orchestrator_node(
        {
            "task_status": {"flight": "pending"},
        }
    )

    assert calls == [({"task_status": {"flight": "pending"}}, 1)]
    assert result["orchestration_steps"] == 1
    assert result["orchestrator_decision"]["next_tasks"] == ["flight_agent"]


def test_orchestrator_node_raises_when_llm_fails_in_debug_mode(monkeypatch):
    def failing_llm_decision(state, orchestration_steps):
        raise OrchestratorError("No valid structured decision.")

    monkeypatch.setattr(
        "app.graph.nodes.orchestrator.validated_llm_decision",
        failing_llm_decision,
    )
    monkeypatch.setattr("app.graph.nodes.orchestrator.settings.debug", True)

    with pytest.raises(OrchestratorError):
        orchestrator_node(
            {
                "task_status": {"accommodation": "pending"},
            }
        )


def test_orchestrator_node_falls_back_when_llm_fails_in_production_mode(monkeypatch):
    def failing_llm_decision(state, orchestration_steps):
        raise OrchestratorError("No valid structured decision.")

    monkeypatch.setattr(
        "app.graph.nodes.orchestrator.validated_llm_decision",
        failing_llm_decision,
    )
    monkeypatch.setattr("app.graph.nodes.orchestrator.settings.debug", False)

    result = orchestrator_node(
        {
            "task_status": {"accommodation": "pending"},
        }
    )

    assert result["orchestration_steps"] == 1
    assert result["orchestrator_decision"]["next_tasks"] == ["accommodation_agent"]
    assert len(result["errors"]) == 1
    assert result["errors"][0].source == "orchestrator"
    assert result["errors"][0].error_type == "llm_decision_failed"
    assert result["errors"][0].retryable is False
