from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass


EPISTEMIC_TIERS = (
    "verified_nasa_finding",
    "project_calculation",
    "scientific_hypothesis",
    "generated_suggestion",
)
PILLARS = ("Prevention", "Detection", "Suppression", "Partial-Gravity", "Methodology")


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source_title: str
    source_path_or_url: str
    psi_id: str | None
    doi: str | None
    pillar: str
    epistemic_tier: str
    text: str
    source_type: str

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def chunk_document(
    text: str,
    *,
    source_title: str,
    source_path_or_url: str,
    psi_id: str | None = None,
    doi: str | None = None,
    pillar: str = "Methodology",
    epistemic_tier: str = "project_calculation",
    source_type: str = "project_document",
    max_chars: int = 1800,
    overlap_chars: int = 180,
) -> list[DocumentChunk]:
    if epistemic_tier not in EPISTEMIC_TIERS:
        raise ValueError(f"Unsupported epistemic tier: {epistemic_tier}")
    if pillar not in PILLARS:
        raise ValueError(f"Unsupported research pillar: {pillar}")
    if max_chars < 1 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Chunk sizes require max_chars > overlap_chars >= 0.")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", normalized) if paragraph.strip()]
    segments: list[str] = []
    for paragraph in paragraphs:
        remaining = paragraph
        while len(remaining) > max_chars:
            split_at = remaining.rfind(" ", 0, max_chars + 1)
            if split_at < max_chars // 2:
                split_at = max_chars
            segments.append(remaining[:split_at].strip())
            remaining = remaining[max(0, split_at - overlap_chars):].strip()
        if remaining:
            segments.append(remaining)

    batches: list[str] = []
    current = ""
    for segment in segments:
        candidate = f"{current}\n\n{segment}" if current else segment
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            batches.append(current)
        current = segment
    if current:
        batches.append(current)

    chunks: list[DocumentChunk] = []
    for index, content in enumerate(batches):
        digest = hashlib.sha256(
            "\0".join((source_path_or_url, psi_id or "", source_title, str(index), content)).encode("utf-8")
        ).hexdigest()[:20]
        chunks.append(
            DocumentChunk(
                chunk_id=f"chunk-{digest}",
                source_title=source_title,
                source_path_or_url=source_path_or_url,
                psi_id=psi_id,
                doi=doi,
                pillar=pillar,
                epistemic_tier=epistemic_tier,
                text=content,
                source_type=source_type,
            )
        )
    return chunks
