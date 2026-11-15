from __future__ import annotations

import importlib
import math
import os
import re
from dataclasses import replace
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from ai.ollama.client import OllamaClient, OllamaError, OllamaUnavailable
from ai.rag.chunker import DocumentChunk, chunk_document
from app.archive import RUN_IDS, get_archive
from src.catalogue import REPOSITORY_SCOPE, load_catalogue


ROOT = Path(__file__).resolve().parents[3]
DOCUMENTS = (
    ("README.md", "Project README", "project_calculation"),
    ("docs/methodology.md", "Scientific methodology", "project_calculation"),
    ("docs/references.md", "NASA PSI references and provenance", "verified_nasa_finding"),
    ("docs/validation.md", "Validation and limitations", "project_calculation"),
    ("docs/dataset_inspection_report.md", "Dataset inspection report", "project_calculation"),
)
WORD_PATTERN = re.compile(r"[a-z0-9]+(?:[./-][a-z0-9]+)*", re.IGNORECASE)
PILLARS = {"Prevention", "Detection", "Suppression"}


def _record_pillar(record: dict) -> str:
    if "PSI-22" == record.get("psi_id") or any("partial" in str(item).lower() for item in record.get("gravity_regimes", [])):
        return "Partial-Gravity"
    for pillar in record.get("pillars", []):
        if pillar in PILLARS:
            return pillar
    return "Methodology"


def _catalogue_text(record: dict) -> str:
    fields = (
        ("NASA PSI identifier", "psi_id"),
        ("Investigation", "name"),
        ("Short name", "short_name"),
        ("Objective", "objective"),
        ("Source findings", "source_findings"),
        ("Pillar", "pillars"),
        ("Research area", "research_area"),
        ("Subresearch area", "subresearch_area"),
        ("Fuel or sample", "fuel_or_sample"),
        ("Hardware rack", "hardware_rack"),
        ("Hardware", "hardware"),
        ("Fuel phase", "fuel_phase"),
        ("Gravity", "gravity_level"),
        ("Gravity regimes", "gravity_regimes"),
        ("Oxygen conditions", "oxygen_recorded"),
        ("Oxygen bounds (% by volume)", "o2_range_pct"),
        ("Pressure conditions", "pressure_recorded"),
        ("Pressure bounds (psi)", "pressure_range_psi"),
        ("Airflow conditions", "airflow_recorded"),
        ("Airflow bounds (cm/s)", "airflow_range_cm_s"),
        ("Sensors and variables", "sensors_variables"),
        ("Predictive variables", "predictive_variables"),
        ("Reported outcomes", "outcomes"),
        ("Terrestrial application", "earth_spinoff"),
        ("Historical incident context", "historical_incident_links"),
        ("Raw data availability", "raw_data_availability"),
        ("Local data status", "local_data_status"),
        ("Verification status", "verification_status"),
    )
    lines = []
    for label, key in fields:
        value = record.get(key)
        if value not in (None, "", [], {}):
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def build_corpus() -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for record in load_catalogue():
        psi_id = record["psi_id"]
        doi = record.get("doi") or None
        if not isinstance(doi, str) or not doi.startswith("10."):
            doi = "psi_record_verified_doi_pending" if psi_id == "PSI-22" else None
        chunks.extend(
            chunk_document(
                _catalogue_text(record),
                source_title=f"{psi_id} · {record.get('short_name', record['name'])}",
                source_path_or_url=record["source_url"],
                psi_id=psi_id,
                doi=doi,
                pillar=_record_pillar(record),
                epistemic_tier="verified_nasa_finding",
                source_type="nasa_psi_catalogue_metadata",
            )
        )

    for item in REPOSITORY_SCOPE["tier2"]:
        text = (
            f"Associated PSI scope entry: {item['name']} ({item['key']}). "
            f"Focus: {item['focus']} Scope status: {item['scope_status']}. "
            "This is project-maintained repository-scope context, not a local measurement or a Tier-1 physics record."
        )
        chunks.extend(
            chunk_document(
                text,
                source_title=f"Tier-2 scope · {item['key']}",
                source_path_or_url="backend/src/catalogue.py#REPOSITORY_SCOPE",
                pillar="Methodology",
                epistemic_tier="project_calculation",
                source_type="project_scope_metadata",
            )
        )

    archive = get_archive()
    for run_id in RUN_IDS:
        summary = archive["summaries"][run_id]
        metrics = archive["metrics"][run_id]
        lag_rows = [
            row for row in archive["lags"]
            if row.get("RunID") == run_id and row.get("Lag") in {"10", "11", "21", "22"}
        ]
        model_rows = [
            row for row in archive["models"]
            if row.get("RunID") == run_id and row.get("ModelType") in {"FullSequenceBest", "ChronologicalHoldout"}
        ]
        exception_ids = sorted(archive["exceptions"][run_id])
        content = "\n".join(
            (
                f"PSI-101 SAME-R archived Pyrell run {run_id}.",
                f"Archived phase summary: {summary}.",
                f"Archived periodicity metrics: {metrics}.",
                f"Selected archived lag-correlation rows: {lag_rows}.",
                f"Exploratory candidate-model records (not a deployed ML model): {model_rows}.",
                f"Phase-exception cycle count: {len(exception_ids)}; first cycle IDs: {exception_ids[:20]}.",
                f"Verified archive checkpoint: {next(item for item in archive['validation'] if item['run_id'] == run_id)}.",
                f"Processing status: {archive['processing_status']} Raw source replay performed: {archive['raw_replay_performed']}.",
                "Exception cycles are classification mismatches, not fires, alarms, or detector failures.",
            )
        )
        chunks.extend(
            chunk_document(
                content,
                source_title=f"PSI-101 SAME-R archived summary · Run {run_id}",
                source_path_or_url="backend/app/archive.py and backend/data/metadata/",
                psi_id="PSI-101",
                doi="10.60555/2np7-jv14",
                pillar="Detection",
                epistemic_tier="project_calculation",
                source_type="verified_archived_summary",
            )
        )

    validation_text = (
        f"PSI-101 SAME-R archive validation. Processing status: {archive['processing_status']} "
        f"Raw source replay performed: {archive['raw_replay_performed']}. "
        f"Per-run reconciliation checks: {archive['validation']}. "
        "These checks validate archived product consistency; they are not independent scientific validation."
    )
    chunks.extend(
        chunk_document(
            validation_text,
            source_title="PSI-101 SAME-R archived validation checkpoints",
            source_path_or_url="backend/app/archive.py and backend/data/metadata/",
            psi_id="PSI-101",
            doi="10.60555/2np7-jv14",
            pillar="Detection",
            epistemic_tier="project_calculation",
            source_type="verified_archived_summary",
        )
    )

    for relative_path, title, tier in DOCUMENTS:
        path = ROOT / relative_path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig")
        document_chunks = chunk_document(
            text,
            source_title=title,
            source_path_or_url=relative_path,
            pillar="Methodology",
            epistemic_tier=tier,
            source_type="project_document",
        )
        if tier == "project_calculation":
            hypothesis_markers = ("hypothesis", "not fitted", "not calibrated", "unvalidated", "surrogate")
            document_chunks = [
                replace(chunk, epistemic_tier="scientific_hypothesis")
                if any(marker in chunk.text.lower() for marker in hypothesis_markers)
                else chunk
                for chunk in document_chunks
            ]
        chunks.extend(document_chunks)
    return chunks


class HybridIndex:
    def __init__(self, chunks: Iterable[DocumentChunk]) -> None:
        self.chunks = list(chunks)
        self._tokens = [self._tokenize(chunk.text) for chunk in self.chunks]
        self._document_frequency: Counter[str] = Counter()
        for tokens in self._tokens:
            self._document_frequency.update(tokens.keys())
        self._dense_vectors: list[list[float]] | None = None
        self._faiss_index = None
        self.embedding_model: str | None = None
        self.embedding_status = "Lexical TF-IDF index active; local embeddings disabled."

    @staticmethod
    def _tokenize(text: str) -> Counter[str]:
        expanded: list[str] = []
        for token in WORD_PATTERN.findall(text):
            normalized = token.lower()
            expanded.append(normalized)
            parts = [part for part in re.split(r"[./-]+", normalized) if part]
            expanded.extend(parts)
            for part in parts:
                if len(part) > 4 and part.endswith("ies"):
                    expanded.append(f"{part[:-3]}y")
                elif len(part) > 4 and part.endswith("s"):
                    expanded.append(part[:-1])
        return Counter(expanded)

    def set_dense_embeddings(self, embeddings: list[list[float]], model: str | None = None) -> None:
        if len(embeddings) != len(self.chunks):
            raise ValueError("Embedding count must match the indexed chunk count.")
        if not embeddings:
            self._dense_vectors = []
            return
        dimensions = len(embeddings[0])
        if dimensions < 1 or any(len(vector) != dimensions for vector in embeddings):
            raise ValueError("Embedding vectors must have one consistent, non-empty dimension.")
        normalized: list[list[float]] = []
        for vector in embeddings:
            norm = math.sqrt(sum(value * value for value in vector))
            if norm == 0:
                raise ValueError("Embedding vectors must not be zero vectors.")
            normalized.append([value / norm for value in vector])
        self._dense_vectors = normalized
        self.embedding_model = model
        try:
            faiss = importlib.import_module("faiss")
            numpy = importlib.import_module("numpy")
        except ImportError:
            self._faiss_index = None
            self.embedding_status = "Ollama embeddings active with cosine similarity; FAISS is not installed."
            return
        index = faiss.IndexFlatIP(dimensions)
        index.add(numpy.asarray(normalized, dtype="float32"))
        self._faiss_index = index
        self.embedding_status = "Ollama embeddings and optional FAISS cosine index active."

    def score(self, query: str, query_embedding: list[float] | None = None) -> list[float]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [0.0] * len(self.chunks)
        query_weights = {
            token: count * (math.log(1 + (len(self.chunks) + 1) / (self._document_frequency[token] + 1)) + 1)
            for token, count in query_tokens.items()
        }
        query_norm = math.sqrt(sum(value * value for value in query_weights.values()))
        if query_norm == 0:
            lexical = [0.0] * len(self.chunks)
        else:
            query_weights = {token: value / query_norm for token, value in query_weights.items()}
            lexical = []
            for tokens in self._tokens:
                weights = {
                    token: count * (math.log(1 + (len(self.chunks) + 1) / (self._document_frequency[token] + 1)) + 1)
                    for token, count in tokens.items()
                }
                norm = math.sqrt(sum(value * value for value in weights.values()))
                lexical.append(
                    sum(query_weights.get(token, 0.0) * value for token, value in weights.items()) / norm
                    if norm
                    else 0.0
                )

        if self._dense_vectors is None or query_embedding is None or not self._dense_vectors:
            return lexical
        if len(query_embedding) != len(self._dense_vectors[0]):
            raise ValueError("Query embedding dimension does not match the document vectors.")
        query_norm = math.sqrt(sum(value * value for value in query_embedding))
        if query_norm == 0:
            return lexical
        dense_query = [value / query_norm for value in query_embedding]
        if self._faiss_index is not None:
            numpy = importlib.import_module("numpy")
            scores, indices = self._faiss_index.search(numpy.asarray([dense_query], dtype="float32"), len(self.chunks))
            dense_scores = [0.0] * len(self.chunks)
            for score, index in zip(scores[0], indices[0]):
                if index >= 0:
                    dense_scores[int(index)] = float(score)
        else:
            dense_scores = [
                sum(left * right for left, right in zip(vector, dense_query))
                for vector in self._dense_vectors
            ]
        return [0.65 * lex + 0.35 * max(0.0, dense) for lex, dense in zip(lexical, dense_scores)]

    def stats(self) -> dict[str, int | str]:
        return {
            "total_chunks": len(self.chunks),
            "sources_covered": len({chunk.source_title for chunk in self.chunks}),
            "tier1_records": len({chunk.psi_id for chunk in self.chunks if chunk.source_type == "nasa_psi_catalogue_metadata"}),
            "archive_runs": len({chunk.source_title.rsplit("Run ", 1)[-1] for chunk in self.chunks if chunk.source_type == "verified_archived_summary" and "Run " in chunk.source_title}),
            "embedding_status": self.embedding_status,
        }


def _enable_optional_embeddings(index: HybridIndex) -> None:
    if os.environ.get("AI_ENABLE_OLLAMA_EMBEDDINGS", "").strip().lower() not in {"1", "true", "yes"}:
        return
    model = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    client = OllamaClient()
    try:
        status = client.status()
        if not status["online"]:
            index.embedding_status = "Ollama embeddings unavailable; deterministic TF-IDF remains active."
            return
        embeddings: list[list[float]] = []
        for start in range(0, len(index.chunks), 24):
            embeddings.extend(client.embed(model, [chunk.text for chunk in index.chunks[start:start + 24]]))
        index.set_dense_embeddings(embeddings, model=model)
    except OllamaUnavailable as exc:
        index.embedding_status = f"Ollama embeddings unavailable; deterministic TF-IDF remains active: {exc}"
    except OllamaError as exc:
        index.embedding_status = f"Ollama embedding error; deterministic TF-IDF remains active: {exc}"


@lru_cache(maxsize=1)
def get_index() -> HybridIndex:
    index = HybridIndex(build_corpus())
    _enable_optional_embeddings(index)
    return index
