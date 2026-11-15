from __future__ import annotations

from typing import Iterable

from ai.rag.chunker import DocumentChunk


SAFETY_PRINCIPLES = (
    "Never fabricate NASA datasets.",
    "Never invent experimental results.",
    "Never claim an unvalidated model is scientifically accurate.",
    "Clearly identify synthetic data.",
    "Distinguish measured data from calculated values.",
    "Preserve original dataset provenance.",
    "Record units and measurement conditions.",
    "Prevent training/test data leakage.",
    "Report uncertainty.",
    "Keep an audit trail.",
    "Require human review for scientific interpretations.",
    "Do not issue physical spacecraft control commands.",
    "Do not operate fire-suppression equipment.",
    "Do not represent the platform as NASA-approved or flight-certified.",
)

SYSTEM_PROMPT = """You are the local FIRELYTICS AI scientific research assistant.
Use only the supplied retrieved context and explicitly supplied scenario values.
Do not use model memory as a source of NASA facts. If evidence is absent, say so.
Never invent citations, DOIs, measurements, study findings, or validation claims.
Keep NASA PSI metadata, archived/project calculations, scientific hypotheses, and
your own human-review-required suggestions in separate sections. A code
visualization surrogate is not a validated physical law or prediction. Never
issue spacecraft commands or suppression operating instructions. Your answer
must remain a research explanation, not a safety decision.

The only permitted claim classifications are:
1. verified_nasa_finding — directly supported by the included NASA record/source;
2. project_calculation — a documented project calculation or archived derived result;
3. scientific_hypothesis — an explicitly bounded, unvalidated interpretation;
4. generated_suggestion — a proposal requiring human scientific review.

Mandatory scientific reliability and safety principles:
""" + "\n".join(f"{index}. {principle}" for index, principle in enumerate(SAFETY_PRINCIPLES, 1))


def build_user_prompt(
    question: str,
    chunks: Iterable[DocumentChunk],
    scenario_context: dict | None = None,
) -> str:
    evidence = []
    for chunk in chunks:
        evidence.append(
            {
                "chunk_id": chunk.chunk_id,
                "source_title": chunk.source_title,
                "source_path_or_url": chunk.source_path_or_url,
                "psi_id": chunk.psi_id,
                "doi": chunk.doi,
                "epistemic_tier": chunk.epistemic_tier,
                "excerpt": chunk.text,
            }
        )
    return (
        f"Research task/question:\n{question}\n\n"
        f"Explicit scenario context (not independently verified measurements):\n{scenario_context or {}}\n\n"
        f"Retrieved evidence (cite only these exact source identifiers):\n{evidence}\n\n"
        "Write a concise answer with inline [PSI-XX] or [Doc] markers only when "
        "the matching source is present above. Separate facts from calculations, "
        "hypotheses, and suggestions. State when the supplied evidence is insufficient."
    )
