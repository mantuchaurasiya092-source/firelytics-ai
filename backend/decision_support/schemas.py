from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ScenarioContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission: str = Field(default="Decision support scenario", min_length=1, max_length=120)
    gravity: str = Field(default="Unknown", max_length=80)
    gravity_g: float | None = Field(default=None, ge=0, le=2)
    oxygen_pct: float | None = Field(default=None, ge=0, le=100)
    pressure_psi: float | None = Field(default=None, gt=0, le=30)
    pressure_atm: float | None = Field(default=None, gt=0, le=3)
    airflow_cms: float | None = Field(default=None, ge=0, le=250)
    airflow_cm_s: float | None = Field(default=None, ge=0, le=250)
    material: str = Field(default="", max_length=200)
    pillar: Literal["Any pillar", "Prevention", "Detection", "Suppression"] = "Any pillar"


class DecisionSupportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: ScenarioContext
    telemetry_state: dict[str, Any] | None = Field(default=None, max_length=32)
    digital_twin_state: dict[str, Any] | None = Field(default=None, max_length=16)
    ml_state: dict[str, Any] | None = Field(default=None, max_length=32)
    integration_warnings: list[str] = Field(default_factory=list, max_length=10)


class RelevanceItem(BaseModel):
    psi_id: str
    name: str
    match_score: float
    evidence_coverage: float
    source_url: str
    doi: str | None = None
    local_data_status: str | None = None
    interpretation: str


class EvidenceCitation(BaseModel):
    chunk_id: str
    psi_id: str | None = None
    title: str
    doi: str | None = None
    source_path_or_url: str
    relevance_score: float
    excerpt: str
    epistemic_tier: str


class ExecutiveResearchBrief(BaseModel):
    summary: str
    active_scenario_context: dict[str, Any]
    relevance_ranking: list[RelevanceItem]
    anomaly_analysis: dict[str, Any]
    ml_insights: dict[str, Any]
    intervention_comparison: dict[str, Any]
    evidence_gaps: list[dict[str, Any]]
    supporting_citations: list[EvidenceCitation]
    epistemic_separation: dict[str, Any]
    integration_warnings: list[str]
    safety_disclaimer: str
