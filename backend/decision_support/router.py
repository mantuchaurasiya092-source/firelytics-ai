from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ai.rag.indexer import get_index
from ai.retrieval.retriever import Retriever
from decision_support.aggregator import aggregate_system_state
from decision_support.schemas import DecisionSupportRequest, ExecutiveResearchBrief
from decision_support.synthesis import generate_research_brief

router = APIRouter(tags=["scientific decision support"])


def _rag_query(scenario: dict[str, Any]) -> str:
    terms = [
        scenario.get("mission"),
        scenario.get("material"),
        scenario.get("pillar"),
        scenario.get("gravity"),
        "NASA PSI evidence and experimental condition limitations",
    ]
    return " ".join(str(item) for item in terms if item not in (None, ""))


@router.post("/decision-support/synthesize", response_model=ExecutiveResearchBrief)
@router.post("/api/decision-support/synthesize")
def synthesize_decision_support(request: DecisionSupportRequest) -> ExecutiveResearchBrief:
    scenario = request.scenario.model_dump(exclude_none=True)
    state = aggregate_system_state(
        scenario=scenario,
        telemetry=request.telemetry_state,
        ml_results=request.ml_state,
        twin_results=request.digital_twin_state,
        integration_warnings=request.integration_warnings,
    )
    try:
        retrieved = Retriever(get_index()).retrieve(_rag_query(scenario), top_k=8)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"Local RAG evidence retrieval failed: {exc}") from exc

    return ExecutiveResearchBrief.model_validate(
        generate_research_brief(
            state,
            [item.citation() for item in retrieved],
        )
    )
