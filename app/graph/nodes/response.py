from langchain_core.messages import AIMessage

from app.graph.state import TravelState


def response_node(state: TravelState):
    lines = ["Travel planner mock response"]

    if state.get("missing_required_fields"):
        fields = ", ".join(state["missing_required_fields"])
        lines.append(f"I need a bit more information before continuing: {fields}.")

    if state.get("ranked_flights"):
        flight = state["ranked_flights"][0]
        lines.append(
            f"Top flight: {flight.airline}, {flight.stops} stop(s), "
            f"{flight.total_price:.0f} {flight.currency}."
        )

    if state.get("ranked_accommodations"):
        accommodation = state["ranked_accommodations"][0]
        lines.append(
            f"Top stay: {accommodation.name} in {accommodation.location}, "
            f"{accommodation.total_price:.0f} {accommodation.currency}."
        )

    if state.get("web_search_results"):
        names = ", ".join(result.name for result in state["web_search_results"][:3])
        lines.append(f"Destination ideas: {names}.")

    if state.get("current_itinerary"):
        itinerary = state["current_itinerary"]
        lines.append(f"Itinerary v{state.get('itinerary_version', 1)}: {len(itinerary.days)} days.")

    final_response = "\n".join(lines)
    return {
        "final_response": final_response,
        "messages": [AIMessage(content=final_response)],
    }
