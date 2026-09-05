from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes.accommodation import accommodation_node
from app.graph.nodes.destination_research import destination_research_node
from app.graph.nodes.fan_in import fan_in_node
from app.graph.nodes.flight import flight_node
from app.graph.nodes.itinerary_planner import itinerary_planner_node
from app.graph.nodes.orchestrator import orchestrator_node, route_orchestrator
from app.graph.nodes.ranking import ranking_node
from app.graph.nodes.response import response_node
from app.graph.nodes.task_status import task_status_node
from app.graph.nodes.turn_interpreter import turn_interpreter_node
from app.graph.nodes.user_clarification import user_clarification_node
from app.graph.state import TravelState


def build_graph():
    builder = StateGraph(TravelState)

    builder.add_node("turn_interpreter", turn_interpreter_node)
    builder.add_node("task_status", task_status_node)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("flight_agent", flight_node)
    builder.add_node("accommodation_agent", accommodation_node)
    builder.add_node("destination_research_agent", destination_research_node)
    builder.add_node("fan_in", fan_in_node)
    builder.add_node("ranking", ranking_node)
    builder.add_node("itinerary_planner_agent", itinerary_planner_node)
    builder.add_node("user_clarification", user_clarification_node)
    builder.add_node("response_agent", response_node)

    builder.add_edge(START, "turn_interpreter")
    builder.add_edge("turn_interpreter", "task_status")
    builder.add_edge("task_status", "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_orchestrator,
        {
            "flight_agent": "flight_agent",
            "accommodation_agent": "accommodation_agent",
            "destination_research_agent": "destination_research_agent",
            "ranking": "ranking",
            "itinerary_planner_agent": "itinerary_planner_agent",
            "user_clarification": "user_clarification",
            "response_agent": "response_agent",
        },
    )
    builder.add_edge("flight_agent", "fan_in")
    builder.add_edge("accommodation_agent", "fan_in")
    builder.add_edge("destination_research_agent", "fan_in")
    builder.add_edge("fan_in", "orchestrator")
    builder.add_edge("ranking", "orchestrator")
    builder.add_edge("itinerary_planner_agent", "orchestrator")
    builder.add_edge("user_clarification", "response_agent")
    builder.add_edge("response_agent", END)

    return builder.compile(checkpointer=InMemorySaver())


@lru_cache
def get_graph():
    return build_graph()
