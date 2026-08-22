from pathlib import Path

from app.retrieval.knowledge import KnowledgeRetriever


KNOWLEDGE_DIR = Path("data/knowledge")


QUERIES = [
    "How long does standard shipping take?",
    "What is the return policy?",
    "Can I cancel my order?",
    "Can I change the color of my shoes after delivery?",
    "What is the weather in Singapore today?",
    "Can you tell me a joke?",
]


def main():
    retriever = KnowledgeRetriever(KNOWLEDGE_DIR)

    for query in QUERIES:
        print("\n" + "=" * 70)
        print(f"QUERY: {query}")
        print("=" * 70)

        results = retriever.search(query, top_k=3)

        for result in results:
            print(
                f"\nScore: {result.score:.4f}"
                f"\nSource: {result.source}"
                f"\nContent: {result.content[:200]}..."
            )


if __name__ == "__main__":
    main()