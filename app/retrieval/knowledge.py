from pathlib import Path

import numpy as np
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

MIN_SIMILARITY = 0.50


class KnowledgeChunk(BaseModel):
    source: str
    content: str
    score: float


class KnowledgeRetriever:
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        self.chunks: list[KnowledgeChunk] = []
        self.embeddings: np.ndarray | None = None

        self._load_documents()

    def _load_documents(self) -> None:
        for path in sorted(self.knowledge_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8").strip()

            if not content:
                continue

            self.chunks.append(
                KnowledgeChunk(
                    source=path.name,
                    content=content,
                    score=0.0,
                )
            )

        if not self.chunks:
            raise ValueError("Knowledge base contains no documents.")

        texts = [chunk.content for chunk in self.chunks]

        self.embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
        )

    def search(self, query: str, top_k: int = 3) -> list[KnowledgeChunk]:
        if not query.strip():
            return []

        if self.embeddings is None:
            raise RuntimeError("Knowledge base has not been initialized.")

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
        )[0]

        scores = self.embeddings @ query_embedding

        top_indices = np.argsort(scores)[::-1]

        results = []

        for index in top_indices:
            score = float(scores[index])

            if score < MIN_SIMILARITY:
                break

            chunk = self.chunks[index]

            results.append(
                chunk.model_copy(
                    update={"score": score}
                )
            )

            if len(results) >= top_k:
                break

        return results