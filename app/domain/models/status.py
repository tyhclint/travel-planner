from typing import Literal

TaskName = Literal["flight", "accommodation", "destination_research", "itinerary", "ranking"]
TaskStatus = Literal["not_required", "pending", "running", "completed", "stale", "failed"]

ALL_TASK_NAMES: tuple[TaskName, ...] = (
    "flight",
    "accommodation",
    "destination_research",
    "itinerary",
    "ranking",
)

DEFAULT_TASK_STATUS: dict[TaskName, TaskStatus] = {
    task_name: "not_required" for task_name in ALL_TASK_NAMES
}

RUNNABLE_TASK_STATUSES: set[TaskStatus] = {"pending", "stale"}
REQUESTABLE_TASK_STATUSES: set[TaskStatus] = {"not_required", "failed"}


def normalize_task_status(
    current_status: dict[TaskName, TaskStatus] | None = None,
) -> dict[TaskName, TaskStatus]:
    statuses = DEFAULT_TASK_STATUS.copy()
    if current_status:
        statuses.update(current_status)
    return statuses
