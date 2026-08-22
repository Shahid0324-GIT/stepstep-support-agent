import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from app.agent.context import AgentContext
from app.agent.agent import SupportAgent
from app.observability.logger import configure_logging
from app.retrieval.knowledge import KnowledgeRetriever
from app.tools.knowledge import KnowledgeTool


load_dotenv()
configure_logging()


def main():
    client = Groq(
        api_key=os.environ["GROQ_API_KEY"],
    )

    retriever = KnowledgeRetriever(
        Path("data/knowledge")
    )

    knowledge_tool = KnowledgeTool(retriever)

    agent = SupportAgent(
        client=client,
        model=os.environ["GROQ_MODEL"],
        knowledge_tool=knowledge_tool,
    )

    response = agent.chat(
    message="I want to exchange ORD-1001 for a different size.",
    context=AgentContext(
        request_id="req-escalation-002",
        customer_id="CUST-001",
    ),

)

    print("\nAgent:")
    print(response)


if __name__ == "__main__":
    main()