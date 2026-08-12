from app.domain.invalidation import invalidate_stale_tasks
from app.graph.state import TravelState


def dependency_invalidation_node(state: TravelState):
    return {
        "task_status": invalidate_stale_tasks(
            changed_fields=state.get("changed_fields", []),
            current_status=state.get("task_status", {}),
        )
    }
