from pathlib import Path

from app.tools.knowledge import KnowledgeTool
from app.retrieval.knowledge import KnowledgeRetriever


def main() -> None:
    retriever = KnowledgeRetriever(
        knowledge_dir=Path("data/knowledge"),
    )

    tool = KnowledgeTool(retriever)

    result = tool.search(
        query=(
            "There is no exchange policy in your system. "
            "Can you tell me how I can exchange ORD-1001?"
        )
    )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()