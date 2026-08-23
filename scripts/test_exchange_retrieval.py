from pathlib import Path

from app.retrieval.knowledge import KnowledgeRetriever


def main() -> None:
    retriever = KnowledgeRetriever(
        knowledge_dir=Path("data/knowledge"),
    )

    query = (
        "There is no exchange policy in your system. "
        "Can you tell me how I can exchange ORD-1001?"
    )

    results = retriever.search(query)

    print("=" * 60)
    print("EXCHANGE RETRIEVAL DIAGNOSTIC")
    print("=" * 60)

    print(f"\nQuery:\n{query}\n")

    if not results:
        print("No results found.")
        return

    for result in results:
        print(f"Score: {result.score:.4f}")
        print(f"Source: {result.source}")
        print(f"Content:\n{result.content}")
        print("-" * 60)


if __name__ == "__main__":
    main()