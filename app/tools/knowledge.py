from pydantic import BaseModel

from app.retrieval.knowledge import KnowledgeRetriever, KnowledgeChunk


class KnowledgeToolResponse(BaseModel):
    found: bool
    results: list[KnowledgeChunk]
    message: str


class KnowledgeTool:
    def __init__(self, retriever: KnowledgeRetriever):
        self.retriever = retriever

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> KnowledgeToolResponse:

        results = self.retriever.search(
            query,
            top_k=top_k,
        )

        if not results:
            return KnowledgeToolResponse(
                found=False,
                results=[],
                message=(
                    "No sufficiently relevant information was found "
                    "in the StepStep knowledge base. Do not infer or "
                    "invent an answer from unrelated policies."
                ),
            )

        return KnowledgeToolResponse(
            found=True,
            results=results,
            message="Relevant knowledge found.",
        )