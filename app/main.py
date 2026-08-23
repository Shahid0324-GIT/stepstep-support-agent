import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from groq import Groq

from app.agent.agent import SupportAgent
from app.api.routes import get_agent, router
from app.observability.logger import configure_logging
from app.retrieval.knowledge import KnowledgeRetriever
from app.tools.knowledge import KnowledgeTool


load_dotenv()
configure_logging()

KNOWLEDGE_DIR = Path("data/knowledge")


def create_agent() -> SupportAgent:
    groq_api_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL")

    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    if not groq_model:
        raise RuntimeError("GROQ_MODEL is not configured.")

    retriever = KnowledgeRetriever(
        knowledge_dir=KNOWLEDGE_DIR,
    )

    knowledge_tool = KnowledgeTool(
        retriever=retriever,
    )

    client = Groq(
        api_key=groq_api_key,
    )

    return SupportAgent(
        client=client,
        model=groq_model,
        knowledge_tool=knowledge_tool,
    )


agent = create_agent()

app = FastAPI(
    title="StepStep Support Agent",
    version="0.1.0",
)

app.dependency_overrides[get_agent] = lambda: agent

app.include_router(
    router,
    prefix="/api/v1",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}