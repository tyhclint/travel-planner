from app.domain.invalidation import invalidate_stale_tasks, mark_required_tasks
from app.domain.models.status import DEFAULT_TASK_STATUS, normalize_task_status


def test_normalize_task_status_includes_every_known_task():
    assert normalize_task_status({"flight": "completed"}) == {
        **DEFAULT_TASK_STATUS,
        "flight": "completed",
    }


def test_flight_request_marks_only_flight_and_ranking_pending():
    statuses = mark_required_tasks(["flight"])

    assert statuses["flight"] == "pending"
    assert statuses["ranking"] == "pending"
    assert statuses["accommodation"] == "not_required"
    assert statuses["destination_research"] == "not_required"
    assert statuses["itinerary"] == "not_required"


def test_destination_research_request_does_not_require_ranking():
    statuses = mark_required_tasks(["destination_research"])

    assert statuses["destination_research"] == "pending"
    assert statuses["ranking"] == "not_required"


def test_mark_required_tasks_keeps_stale_status():
    statuses = mark_required_tasks(
        ["flight"],
        {
            **DEFAULT_TASK_STATUS,
            "flight": "stale",
            "ranking": "stale",
        },
    )

    assert statuses["flight"] == "stale"
    assert statuses["ranking"] == "stale"


def test_origin_change_marks_completed_flight_ranking_and_itinerary_stale():
    statuses = invalidate_stale_tasks(
        ["origin"],
        {
            **DEFAULT_TASK_STATUS,
            "flight": "completed",
            "ranking": "completed",
            "itinerary": "completed",
        },
    )

    assert statuses["flight"] == "stale"
    assert statuses["ranking"] == "stale"
    assert statuses["itinerary"] == "stale"
