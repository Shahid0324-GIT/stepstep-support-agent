import json
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

from tests.evals.test_agent_scenarios import CASES


load_dotenv()
configure_logging()
KNOWLEDGE_DIR = Path("data/knowledge")

def build_agent() -> SupportAgent:
    client = Groq()

    retriever = KnowledgeRetriever(knowledge_dir=KNOWLEDGE_DIR,)
    knowledge_tool = KnowledgeTool(retriever)

    return SupportAgent(
        client=client,
        model="openai/gpt-oss-20b",
        knowledge_tool=knowledge_tool,
    )


def run_case(agent: SupportAgent, case):
    events = []

    set_event_sink(events.append)

    request_id = f"eval-{uuid4()}"

    started = time.perf_counter()

    try:
        response = agent.chat(
            message=case.message,
            context=AgentContext(
                request_id=request_id,
                customer_id=case.customer_id,
            ),
        )

        duration_ms = round(
            (time.perf_counter() - started) * 1000,
            2,
        )

        return {
            "name": case.name,
            "customer_id": case.customer_id,
            "message": case.message,
            "expected_behavior": case.expected_behavior,
            "response": response,
            "duration_ms": duration_ms,
            "tool_calls": [
                event.details.get("tool_name")
                for event in events
                if event.event_type == "tool_call"
            ],
            "events": [
                event.model_dump(mode="json")
                for event in events
            ],
        }

    finally:
        set_event_sink(None)


def main():
    agent = build_agent()

    results = []

    print("=" * 60)
    print("STEPSTEP SUPPORT AGENT EVALUATION")
    print("=" * 60)

    for case in CASES:
        print(f"\nRunning: {case.name}")

        result = run_case(agent, case)
        results.append(result)

        print(f"Tools: {result['tool_calls']}")
        print(f"Response: {result['response']}")
        print(f"Duration: {result['duration_ms']} ms")

    output_path = Path("assessment") / "evaluation_results.json"
    output_path.parent.mkdir(exist_ok=True)

    output_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print(f"Results saved to: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()