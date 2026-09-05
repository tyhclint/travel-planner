"""Shared workflow entry point used by HTTP and MCP adapters."""

from langchain_core.messages import HumanMessage

from app.graph.builder import get_graph


def run_travel_turn(message: str, thread_id: str) -> str:
    if not message.strip():
        raise ValueError("message must not be empty")

    result = get_graph().invoke(
        {"messages": [HumanMessage(content=message)], "latest_user_input": message},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result.get("final_response", "The travel workflow completed without a response.")
