from pathlib import Path

from app.retrieval.knowledge import KnowledgeRetriever


KNOWLEDGE_DIR = Path("data/knowledge")


def test_returns_question_retrieves_return_policy():
    retriever = KnowledgeRetriever(KNOWLEDGE_DIR)

    results = retriever.search(
        "Can I send my shoes back?",
        top_k=3,
    )

    assert results
    assert results[0].source == "returns.md"


def test_cancellation_question_retrieves_cancellation_policy():
    retriever = KnowledgeRetriever(KNOWLEDGE_DIR)

    results = retriever.search(
        "Can I cancel my order after it has shipped?",
        top_k=3,
    )

    assert results
    assert results[0].source == "cancellations.md"


def test_shipping_question_retrieves_shipping_policy():
    retriever = KnowledgeRetriever(KNOWLEDGE_DIR)

    results = retriever.search(
        "How long does standard shipping take?",
        top_k=3,
    )

    assert results
    assert results[0].source == "shipping.md"


def test_empty_query_returns_no_results():
    retriever = KnowledgeRetriever(KNOWLEDGE_DIR)

    assert retriever.search("   ") == []
    
def test_unrelated_question_returns_no_results():
    retriever = KnowledgeRetriever(KNOWLEDGE_DIR)

    results = retriever.search(
        "What is the weather in Singapore today?"
    )

    assert results == []
    
def test_unsupported_product_change_question_returns_no_results():
    retriever = KnowledgeRetriever(KNOWLEDGE_DIR)
    results = retriever.search(
        "Can I change the color of my shoes after delivery?"
    )

    assert results == []