from app.domain.models.status import (
    REQUESTABLE_TASK_STATUSES,
    TaskName,
    TaskStatus,
    normalize_task_status,
)
from app.domain.models.workflow import ChangedField, RequestedCapability

DEPENDENCIES: dict[ChangedField, set[TaskName]] = {
    "origin": {"flight", "ranking", "itinerary"},
    "destination": {"flight", "accommodation", "destination_research", "ranking", "itinerary"},
    "travel_dates": {"flight", "accommodation", "destination_research", "ranking", "itinerary"},
    "budget": {"flight", "accommodation", "destination_research", "ranking", "itinerary"},
    "flight_preferences": {"flight", "ranking", "itinerary"},
    "accommodation_preferences": {"accommodation", "ranking", "itinerary"},
    "activity_preferences": {"destination_research", "itinerary"},
    "selected_flight": {"itinerary"},
    "selected_accommodation": {"itinerary"},
    "itinerary_day": {"itinerary"},
}


def mark_required_tasks(
    requested_capabilities: list[RequestedCapability],
    current_status: dict[TaskName, TaskStatus] | None = None,
) -> dict[TaskName, TaskStatus]:
    """ Marks tasks as pending in a fresh run """
    statuses = normalize_task_status(current_status)

    for capability in requested_capabilities:
        if capability in statuses and statuses[capability] in REQUESTABLE_TASK_STATUSES:
            statuses[capability] = "pending"

    if (
        any(capability in requested_capabilities for capability in ("flight", "accommodation"))
        and statuses["ranking"] in REQUESTABLE_TASK_STATUSES
    ):
        statuses["ranking"] = "pending"

    return statuses


def invalidate_stale_tasks(
    changed_fields: list[ChangedField],
    current_status: dict[TaskName, TaskStatus],
) -> dict[TaskName, TaskStatus]:
    """ Marks completed tasks as stale if they depend on changed fields. """
    statuses = normalize_task_status(current_status)

    for changed_field in changed_fields:
        for task in DEPENDENCIES.get(changed_field, set()):
            if statuses[task] == "completed":
                statuses[task] = "stale"

    return statuses
