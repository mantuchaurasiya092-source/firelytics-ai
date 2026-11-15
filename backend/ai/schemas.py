from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


TaskType = Literal[
    "project_overview",
    "catalogue_search",
    "retrieve_documents",
    "explain_terminology",
    "explain_partial_gravity",
    "interpret_simulation",
    "explain_ml_predictions",
    "compare_investigations",
    "identify_evidence_gaps",
    "generate_summary",
    "generate_proposal",
    "generate_report",
    "qa_with_citations",
]
Pillar = Literal["Prevention", "Detection", "Suppression", "Partial-Gravity", "Methodology"]
EpistemicTier = Literal[
    "verified_nasa_finding",
    "project_calculation",
    "scientific_hypothesis",
    "generated_suggestion",
]


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class RetrieveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    psi_ids: list[str] | None = Field(default=None, max_length=24)
    pillar: Pillar | None = None
    epistemic_tier: EpistemicTier | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=4000)
    task_type: TaskType = "qa_with_citations"
    model: str | None = Field(default=None, max_length=160)
    scenario_context: dict[str, Any] | None = None
    psi_ids: list[str] | None = Field(default=None, max_length=24)
    pillar: Pillar | None = None
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    session_id: str | None = Field(default=None, min_length=1, max_length=120)


class SimulationExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    simulation_inputs: dict[str, Any] | None = None
    simulation_outputs: dict[str, Any] | None = None
    simulation: dict[str, Any] | None = None
    scenario_context: dict[str, Any] | None = None
    message: str | None = Field(default=None, max_length=4000)
    model: str | None = Field(default=None, max_length=160)
    psi_ids: list[str] | None = Field(default=None, max_length=24)
    session_id: str | None = Field(default=None, min_length=1, max_length=120)


class GenerateReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_context: dict[str, Any] | None = None
    selected_psi_ids: list[str] = Field(default_factory=list, max_length=24)
    report_type: Literal["report", "proposal"] = "report"
    message: str | None = Field(default=None, max_length=4000)
    model: str | None = Field(default=None, max_length=160)
    session_id: str | None = Field(default=None, min_length=1, max_length=120)
