from app.domain.invalidation import invalidate_stale_tasks, mark_required_tasks
from app.graph.state import TravelState


def task_status_node(state: TravelState):
    statuses = invalidate_stale_tasks(
        changed_fields=state.get("changed_fields", []),
        current_status=state.get("task_status", {}),
    )

    statuses = mark_required_tasks(
        requested_capabilities=state.get("requested_capabilities", []),
        current_status=statuses,
    )

    return {"task_status": statuses}
