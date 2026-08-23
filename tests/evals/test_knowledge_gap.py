import time
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from groq import Groq

from app.agent.agent import SupportAgent
from app.agent.context import AgentContext
from app.observability.logger import configure_logging, set_event_sink
from app.retrieval.knowledge import KnowledgeRetriever
from app.tools.knowledge import KnowledgeTool


load_dotenv()
configure_logging()

KNOWLEDGE_DIR = Path("data/knowledge")


def build_agent() -> SupportAgent:
    client = Groq()

    retriever = KnowledgeRetriever(
        knowledge_dir=KNOWLEDGE_DIR,
    )

    knowledge_tool = KnowledgeTool(retriever)

    return SupportAgent(
        client=client,
        model="openai/gpt-oss-20b",
        knowledge_tool=knowledge_tool,
    )


def main() -> None:
    agent = build_agent()

    events = []
    set_event_sink(events.append)

    request_id = f"eval-knowledge-gap-{uuid4()}"

    message = (
        "There is no exchange policy in your system. "
        "Can you tell me how I can exchange ORD-1001?"
    )

    started = time.perf_counter()

    try:
        response = agent.chat(
            message=message,
            context=AgentContext(
                request_id=request_id,
                customer_id="CUST-001",
            ),
        )

        duration_ms = round(
            (time.perf_counter() - started) * 1000,
            2,
        )

    finally:
        set_event_sink(None)

    tool_calls = [
        event.details.get("tool_name")
        for event in events
        if event.event_type == "tool_call"
    ]

    print("\n" + "=" * 60)
    print("KNOWLEDGE GAP BASELINE TEST")
    print("=" * 60)

    print(f"\nRequest ID: {request_id}")
    print(f"Message: {message}")
    print(f"\nTool calls: {tool_calls}")
    print(f"\nResponse:\n{response}")
    print(f"\nDuration: {duration_ms} ms")

    print("\n" + "-" * 60)
    print("EVENT TRACE")
    print("-" * 60)

    for event in events:
        print(
            f"{event.event_type}: "
            f"{event.details}"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()