from app.domain.scoring import rank_accommodations, rank_flights
from app.graph.state import TravelState


def ranking_node(state: TravelState):
    ranked_flights = rank_flights(state.get("flight_results", []), state["preferences"])
    ranked_accommodations = rank_accommodations(
        state.get("accommodation_results", []),
        state["preferences"],
    )

    return {
        "ranked_flights": ranked_flights,
        "ranked_accommodations": ranked_accommodations,
        "task_status": {"ranking": "completed"},
    }
