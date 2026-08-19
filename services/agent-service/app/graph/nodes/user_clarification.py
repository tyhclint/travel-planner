from app.graph.state import TravelState


def user_clarification_node(state: TravelState):
    fields = ", ".join(state.get("missing_required_fields", []))
    return {"final_response": f"Please provide the missing required fields: {fields}."}
