"""Interactive CLI client for a checkpointed LangGraph travel thread."""

import argparse
import sys
from uuid import uuid4

from langchain_core.messages import HumanMessage

from app.graph.builder import get_graph


def run_turn(graph, thread_id: str, message: str) -> str:
    result = graph.invoke(
        {"messages": [HumanMessage(content=message)], "latest_user_input": message},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result.get("final_response", "The workflow completed without a response.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the travel planner graph.")
    parser.add_argument("--thread-id", default=f"cli-{uuid4().hex[:8]}")
    parser.add_argument("message", nargs="?", help="Run one turn and exit.")
    args = parser.parse_args()
    graph = get_graph()

    if args.message:
        print(run_turn(graph, args.thread_id, args.message))
        return

    print(f"Travel planner thread: {args.thread_id}")
    print("Type a message, or 'exit' to stop.")
    for line in sys.stdin:
        message = line.strip()
        if message.lower() in {"exit", "quit"}:
            break
        if message:
            try:
                print(run_turn(graph, args.thread_id, message))
            except Exception as exc:
                print(f"Workflow error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
