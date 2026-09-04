from app.domain.models.orchestrator import OrchestratorDecision
from app.domain.orchestration.policy import (
    MAX_ORCHESTRATION_STEPS,
    apply_deterministic_policy,
    deterministic_guardrail_decision,
    fallback_decision,
)


def test_guardrail_routes_to_response_at_max_steps():
    decision = deterministic_guardrail_decision({}, MAX_ORCHESTRATION_STEPS)

    assert decision is not None
    assert decision.next_tasks == ["response_agent"]
    assert decision.can_answer_now is True


def test_guardrail_routes_to_clarification_when_required_fields_are_missing():
    decision = deterministic_guardrail_decision(
        {"missing_required_fields": ["destination", "budget"]},
        1,
    )

    assert decision is not None
    assert decision.next_tasks == ["user_clarification"]
    assert decision.needs_clarification is True
    assert decision.clarification_fields == ["destination", "budget"]


def test_guardrail_returns_none_when_no_hard_stop_applies():
    assert deterministic_guardrail_decision({"task_status": {"flight": "pending"}}, 1) is None


def test_fallback_runs_runnable_independent_tasks_in_parallel():
    decision = fallback_decision(
        {
            "task_status": {
                "flight": "pending",
                "accommodation": "stale",
                "destination_research": "pending",
                "itinerary": "pending",
            }
        },
        1,
    )

    assert decision.next_tasks == [
        "flight_agent",
        "accommodation_agent",
        "destination_research_agent",
    ]


def test_fallback_runs_itinerary_after_independent_tasks_are_not_runnable():
    decision = fallback_decision(
        {
            "task_status": {
                "flight": "completed",
                "accommodation": "completed",
                "destination_research": "completed",
                "itinerary": "pending",
            }
        },
        1,
    )

    assert decision.next_tasks == ["itinerary_planner_agent"]


def test_fallback_routes_to_response_when_no_runnable_work_remains():
    decision = fallback_decision(
        {
            "task_status": {
                "flight": "completed",
                "accommodation": "not_required",
                "destination_research": "completed",
                "itinerary": "completed",
                "ranking": "completed",
            }
        },
        1,
    )

    assert decision.next_tasks == ["response_agent"]
    assert decision.can_answer_now is True


def test_fallback_uses_guardrail_when_present():
    decision = fallback_decision(
        {"missing_required_fields": ["origin"]},
        1,
    )

    assert decision.next_tasks == ["user_clarification"]
    assert decision.clarification_fields == ["origin"]


def test_policy_replaces_premature_response_with_fallback():
    decision = apply_deterministic_policy(
        {"task_status": {"flight": "pending"}},
        OrchestratorDecision(
            next_tasks=["response_agent"],
            can_answer_now=True,
            reason="The LLM thinks the answer is ready.",
        ),
    )

    assert decision.next_tasks == ["flight_agent"]
    assert decision.can_answer_now is False


def test_policy_replaces_completed_task_without_rerun_permission():
    decision = apply_deterministic_policy(
        {
            "task_status": {
                "flight": "completed",
                "accommodation": "pending",
            }
        },
        OrchestratorDecision(
            next_tasks=["flight_agent"],
            reason="The LLM wants to run flights again.",
        ),
    )

    assert decision.next_tasks == ["accommodation_agent"]


def test_policy_allows_completed_task_with_rerun_permission():
    llm_decision = OrchestratorDecision(
        next_tasks=["flight_agent"],
        reason="The user changed a flight preference.",
        rerun_completed_tasks=["flight"],
    )

    decision = apply_deterministic_policy(
        {"task_status": {"flight": "completed"}},
        llm_decision,
    )

    assert decision == llm_decision


def test_policy_preserves_valid_runnable_llm_decision():
    llm_decision = OrchestratorDecision(
        next_tasks=["flight_agent"],
        reason="Flight work is pending.",
    )

    decision = apply_deterministic_policy(
        {"task_status": {"flight": "pending"}},
        llm_decision,
    )

    assert decision == llm_decision
