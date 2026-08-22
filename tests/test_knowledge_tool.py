from pathlib import Path

from app.retrieval.knowledge import KnowledgeRetriever
from app.tools.knowledge import KnowledgeTool


KNOWLEDGE_DIR = Path("data/knowledge")


def create_tool() -> KnowledgeTool:
    retriever = KnowledgeRetriever(KNOWLEDGE_DIR)
    return KnowledgeTool(retriever)


def test_knowledge_tool_returns_relevant_results():
    tool = create_tool()

    result = tool.search("Can I return my shoes?")

    assert result.found is True
    assert result.results
    assert result.results[0].source == "returns.md"


def test_knowledge_tool_returns_cancellation_policy():
    tool = create_tool()

    result = tool.search("Can I cancel an order after it has shipped?")

    assert result.found is True
    assert result.results[0].source == "cancellations.md"


def test_knowledge_tool_returns_no_results_for_empty_query():
    tool = create_tool()

    result = tool.search("")

    assert result.found is False
    assert result.results == []