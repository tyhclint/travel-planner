from langchain_core.messages import HumanMessage

from app.graph.builder import build_graph


def main() -> None:
    graph = build_graph()
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="Plan me a cheap 5-day trip from Singapore to Tokyo")
            ],
            "latest_user_input": "Plan me a cheap 5-day trip from Singapore to Tokyo",
        },
        config={"configurable": {"thread_id": "demo-tokyo-trip"}},
    )
    print(result["final_response"])


if __name__ == "__main__":
    main()
