from app.domain.models.status import TaskName, TaskStatus

DEPENDENCIES: dict[str, set[TaskName]] = {
    "origin": {"flight", "ranking", "itinerary"},
    "destination": {"flight", "accommodation", "web_search", "ranking", "itinerary"},
    "travel_dates": {"flight", "accommodation", "web_search", "ranking", "itinerary"},
    "budget": {"flight", "accommodation", "ranking", "itinerary"},
    "flight_preferences": {"flight", "ranking", "itinerary"},
    "accommodation_preferences": {"accommodation", "ranking", "itinerary"},
    "activity_preferences": {"web_search", "itinerary"},
    "selected_flight": {"itinerary"},
    "selected_accommodation": {"itinerary"},
    "itinerary_day": {"itinerary"},
}


def mark_required_tasks(
    requested_capabilities: list[str],
    current_status: dict[str, TaskStatus] | None = None,
) -> dict[str, TaskStatus]:
    statuses: dict[str, TaskStatus] = {
        "flight": "not_required",
        "accommodation": "not_required",
        "web_search": "not_required",
        "itinerary": "not_required",
        "ranking": "not_required",
    }
    if current_status:
        statuses.update(current_status)

    for capability in requested_capabilities:
        if capability in statuses and statuses[capability] in {"not_required", "stale", "failed"}:
            statuses[capability] = "pending"

    if (
        any(capability in requested_capabilities for capability in ("flight", "accommodation"))
        and statuses["ranking"] in {"not_required", "stale", "failed"}
    ):
        statuses["ranking"] = "pending"

    return statuses


def invalidate_stale_tasks(
    changed_fields: list[str],
    current_status: dict[str, TaskStatus],
) -> dict[str, TaskStatus]:
    statuses = current_status.copy()

    for changed_field in changed_fields:
        for task in DEPENDENCIES.get(changed_field, set()):
            if statuses.get(task) == "completed":
                statuses[task] = "stale"

    return statuses
