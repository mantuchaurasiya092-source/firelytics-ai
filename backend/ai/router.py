from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ai.agents.research_agent import ResearchAgent
from ai.ollama.client import OllamaClient, OllamaError
from ai.rag.indexer import get_index
from ai.retrieval.retriever import Retriever
from ai.schemas import ChatRequest, GenerateReportRequest, RetrieveRequest, SimulationExplanationRequest, TaskType
from src.catalogue import REPOSITORY_SCOPE


router = APIRouter(tags=["local scientific research assistant"])
_history: dict[str, list[dict[str, str]]] = {}
_history_lock = Lock()


def _session_history(session_id: str) -> list[dict[str, str]]:
    with _history_lock:
        return list(_history.get(session_id, []))


def _store_turn(session_id: str | None, user_message: str, assistant_message: str) -> None:
    if session_id is None:
        return
    timestamp = datetime.now(timezone.utc).isoformat()
    with _history_lock:
        messages = _history.setdefault(session_id, [])
        messages.extend(
            (
                {"role": "user", "content": user_message, "created_at": timestamp},
                {"role": "assistant", "content": assistant_message, "created_at": timestamp},
            )
        )
        del messages[:-80]
        if len(_history) > 200:
            oldest = next(iter(_history))
            if oldest != session_id:
                del _history[oldest]


def _agent() -> ResearchAgent:
    return ResearchAgent()


@router.get("/ai/status")
@router.get("/api/ai/status")
def ai_status() -> dict[str, Any]:
    ollama = OllamaClient().status()
    index_stats = get_index().stats()
    return {
        **ollama,
        "rag_index": {
            **index_stats,
            "tier1_records_expected": len(REPOSITORY_SCOPE["tier1"]),
            "tier2_scope_records_expected": len(REPOSITORY_SCOPE["tier2"]),
            "corpus_policy": (
                "Approved PSI catalogue metadata, project scope metadata, packaged SAME-R archived summaries, "
                "and named methodology/reference documents only; raw experiment CSVs are excluded."
            ),
        },
    }


@router.post("/ai/retrieve")
@router.post("/api/ai/retrieve")
def ai_retrieve(request: RetrieveRequest) -> dict[str, Any]:
    results = Retriever(get_index()).retrieve(
        request.query,
        top_k=request.top_k,
        psi_ids=request.psi_ids,
        pillar=request.pillar,
        epistemic_tier=request.epistemic_tier,
    )
    return {
        "query": request.query,
        "items": [item.to_dict() for item in results],
        "count": len(results),
    }


def _run_agent(
    *,
    message: str,
    task_type: TaskType,
    model: str | None,
    scenario_context: dict[str, Any] | None,
    psi_ids: list[str] | None,
    history: list[dict[str, str]],
    session_id: str | None,
) -> dict[str, Any]:
    try:
        response = _agent().answer(
            message=message,
            task_type=task_type,  # validated by the request schema
            model=model,
            scenario_context=scenario_context,
            psi_ids=psi_ids,
            history=history,
        )
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=f"Local Ollama request failed: {exc}") from exc
    _store_turn(session_id, message, response["answer_markdown"])
    response["session_id"] = session_id
    return response


@router.post("/ai/chat")
@router.post("/api/ai/chat")
def ai_chat(request: ChatRequest) -> dict[str, Any]:
    prior = [turn.model_dump() for turn in request.history]
    if not prior and request.session_id:
        prior = [
            {"role": item["role"], "content": item["content"]}
            for item in _session_history(request.session_id)
        ]
    return _run_agent(
        message=request.message,
        task_type=request.task_type,
        model=request.model,
        scenario_context=request.scenario_context,
        psi_ids=request.psi_ids,
        history=prior,
        session_id=request.session_id,
    )


@router.post("/ai/explain-simulation")
@router.post("/api/ai/explain-simulation")
def explain_simulation(request: SimulationExplanationRequest) -> dict[str, Any]:
    context: dict[str, Any] = dict(request.scenario_context or {})
    if request.simulation_inputs is not None:
        context["simulation_inputs"] = request.simulation_inputs
    if request.simulation_outputs is not None:
        context["simulation_outputs"] = request.simulation_outputs
    if request.simulation is not None:
        context["simulation"] = request.simulation
    if not any((request.simulation_inputs, request.simulation_outputs, request.simulation, context)):
        raise HTTPException(status_code=422, detail="Provide simulation inputs, outputs, or scenario_context.")
    question = request.message or (
        "Interpret the supplied existing FIRELYTICS screening simulation. Explain its stated inputs and outputs, "
        "distinguish project calculations from NASA evidence, and state that it is not a validated prediction."
    )
    history = _session_history(request.session_id) if request.session_id else []
    return _run_agent(
        message=question,
        task_type="interpret_simulation",
        model=request.model,
        scenario_context=context,
        psi_ids=request.psi_ids,
        history=[{"role": item["role"], "content": item["content"]} for item in history],
        session_id=request.session_id,
    )


@router.post("/ai/generate-report")
@router.post("/api/ai/generate-report")
def generate_report(request: GenerateReportRequest) -> dict[str, Any]:
    task_type = "generate_proposal" if request.report_type == "proposal" else "generate_report"
    selected = request.selected_psi_ids or None
    question = request.message or (
        f"Create a structured {request.report_type} for the supplied scenario and selected NASA PSI investigations. "
        "Use only retrieved sources and include scope, evidence, limitations, and human-review requirements."
    )
    history = _session_history(request.session_id) if request.session_id else []
    return _run_agent(
        message=question,
        task_type=task_type,
        model=request.model,
        scenario_context=request.scenario_context,
        psi_ids=selected,
        history=[{"role": item["role"], "content": item["content"]} for item in history],
        session_id=request.session_id,
    )


@router.get("/ai/history")
@router.get("/api/ai/history")
def get_history(session_id: str = Query(default="default", min_length=1, max_length=120)) -> dict[str, Any]:
    return {"session_id": session_id, "messages": _session_history(session_id)}


@router.delete("/ai/history")
@router.delete("/api/ai/history")
def clear_history(session_id: str = Query(default="default", min_length=1, max_length=120)) -> dict[str, Any]:
    with _history_lock:
        _history.pop(session_id, None)
    return {"session_id": session_id, "cleared": True}
