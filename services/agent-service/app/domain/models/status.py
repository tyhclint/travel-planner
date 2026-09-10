from typing import Literal

TaskName = Literal["flight", "accommodation", "itinerary", "ranking"]
TaskStatus = Literal["not_required", "pending", "running", "completed", "stale", "failed"]

ALL_TASK_NAMES: tuple[TaskName, ...] = (
    "flight",
    "accommodation",
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
    """ Create a normalized task status dictionary, filling in any missing tasks with the default status. """
    statuses = DEFAULT_TASK_STATUS.copy()
    if current_status:
        statuses.update(
            {
                task_name: status
                for task_name, status in current_status.items()
                if task_name in ALL_TASK_NAMES
            }
        )
    return statuses
