from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes.accommodation import accommodation_node
from app.graph.nodes.dependency_invalidation import dependency_invalidation_node
from app.graph.nodes.fan_in import fan_in_node
from app.graph.nodes.flight import flight_node
from app.graph.nodes.itinerary import itinerary_node
from app.graph.nodes.orchestrator import orchestrator_node, route_orchestrator
from app.graph.nodes.ranking import ranking_node
from app.graph.nodes.response import response_node
from app.graph.nodes.turn_interpreter import turn_interpreter_node
from app.graph.nodes.user_clarification import user_clarification_node
from app.graph.nodes.web_search import web_search_node
from app.graph.state import TravelState


def build_graph():
    builder = StateGraph(TravelState)

    builder.add_node("turn_interpreter", turn_interpreter_node)
    builder.add_node("dependency_invalidation", dependency_invalidation_node)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("flight_agent", flight_node)
    builder.add_node("accommodation_agent", accommodation_node)
    builder.add_node("fan_in", fan_in_node)
    builder.add_node("ranking", ranking_node)
    builder.add_node("web_search_agent", web_search_node)
    builder.add_node("itinerary_agent", itinerary_node)
    builder.add_node("user_clarification", user_clarification_node)
    builder.add_node("response_agent", response_node)

    builder.add_edge(START, "turn_interpreter")
    builder.add_edge("turn_interpreter", "dependency_invalidation")
    builder.add_edge("dependency_invalidation", "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_orchestrator,
        {
            "flight_agent": "flight_agent",
            "accommodation_agent": "accommodation_agent",
            "ranking": "ranking",
            "web_search_agent": "web_search_agent",
            "itinerary_agent": "itinerary_agent",
            "user_clarification": "user_clarification",
            "response_agent": "response_agent",
        },
    )
    builder.add_edge("flight_agent", "fan_in")
    builder.add_edge("accommodation_agent", "fan_in")
    builder.add_edge("fan_in", "ranking")
    builder.add_edge("ranking", "orchestrator")
    builder.add_edge("web_search_agent", "orchestrator")
    builder.add_edge("itinerary_agent", "orchestrator")
    builder.add_edge("user_clarification", "response_agent")
    builder.add_edge("response_agent", END)

    return builder.compile(checkpointer=InMemorySaver())


@lru_cache
def get_graph():
    return build_graph()
