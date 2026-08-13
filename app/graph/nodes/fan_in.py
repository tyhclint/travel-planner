from app.domain.models.status import normalize_task_status
from app.graph.state import TravelState


def fan_in_node(state: TravelState):
    statuses = normalize_task_status(state.get("task_status"))
    completed = [
        task
        for task in ("flight", "accommodation", "destination_research")
        if statuses[task] == "completed"
    ]
    return {"fan_in_notes": [f"Search tasks complete: {', '.join(completed)}"]}
