from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from ai.ollama.client import OllamaClient, OllamaError
from ai.rag.chunker import DocumentChunk
from ai.rag.indexer import HybridIndex


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: DocumentChunk
    relevance_score: float

    def citation(self) -> dict[str, str | float | None]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "psi_id": self.chunk.psi_id,
            "title": self.chunk.source_title,
            "doi": self.chunk.doi,
            "source_path_or_url": self.chunk.source_path_or_url,
            "relevance_score": self.relevance_score,
            "excerpt": self.chunk.text[:420].strip(),
            "epistemic_tier": self.chunk.epistemic_tier,
        }

    def to_dict(self) -> dict:
        return {
            **self.chunk.to_dict(),
            "relevance_score": self.relevance_score,
            "excerpt": self.chunk.text[:420].strip(),
        }


class Retriever:
    def __init__(self, index: HybridIndex) -> None:
        self.index = index
        self.embedding_client = OllamaClient()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        psi_ids: Iterable[str] | None = None,
        pillar: str | None = None,
        epistemic_tier: str | None = None,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        if top_k < 1 or top_k > 20:
            raise ValueError("top_k must be between 1 and 20.")
        accepted_ids = {value.upper() for value in psi_ids or ()}
        query_embedding = None
        if self.index.embedding_model:
            try:
                query_embedding = self.embedding_client.embed(self.index.embedding_model, [query])[0]
            except OllamaError as exc:
                self.index.embedding_status = f"Query embedding unavailable; deterministic TF-IDF remains active: {exc}"
        raw_scores = self.index.score(query, query_embedding)
        query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        candidates = []
        for chunk, score in zip(self.index.chunks, raw_scores):
            if accepted_ids and (chunk.psi_id or "").upper() not in accepted_ids:
                continue
            if pillar and chunk.pillar != pillar:
                continue
            if epistemic_tier and chunk.epistemic_tier != epistemic_tier:
                continue
            title_terms = set(re.findall(r"[a-z0-9]+", chunk.source_title.lower()))
            if query_terms and title_terms:
                score += 0.25 * len(query_terms & title_terms) / len(query_terms)
            if chunk.psi_id and chunk.psi_id.upper() in query.upper():
                score += 1.0
            if score > 0:
                candidates.append((chunk, score))
        if not candidates:
            return []
        maximum = max(score for _, score in candidates)
        candidates.sort(key=lambda item: (-item[1], item[0].chunk_id))
        return [
            RetrievedChunk(chunk=chunk, relevance_score=round(min(score / maximum, 1.0), 6))
            for chunk, score in candidates[:top_k]
        ]
