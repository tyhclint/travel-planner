from app.graph.state import TravelState


def fan_in_node(state: TravelState):
    completed = [
        task
        for task in ("flight", "accommodation")
        if state.get("task_status", {}).get(task) == "completed"
    ]
    return {"fan_in_notes": [f"Search tasks complete: {', '.join(completed)}"]}
