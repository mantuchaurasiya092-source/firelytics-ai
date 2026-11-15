from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaselineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oxygen_pct: float = Field(ge=0, le=100)
    pressure_psi: float = Field(gt=0, le=30)
    airflow_cms: float = Field(ge=0, le=250)
    gravity_g: float = Field(ge=0, le=2)
    temp_k: float | None = Field(default=None, gt=0, le=5000)
    flame_volume_m3: float | None = Field(default=None, gt=0, le=1_000_000)


class InterventionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["ventilation_cutoff", "depressurization", "inert_gas", "gravity_shift"]
    transition_seconds: float = Field(default=30, gt=0, le=3600)
    target_o2_pct: float | None = Field(default=None, ge=0, le=100)
    target_pressure_psi: float | None = Field(default=None, gt=0, le=30)
    target_gravity_g: float | None = Field(default=None, ge=0, le=2)
    inert_species: Literal["CO2", "Helium"] | None = None

    @model_validator(mode="after")
    def require_intervention_targets(self) -> InterventionConfig:
        if self.kind == "depressurization" and (
            self.target_o2_pct is None or self.target_pressure_psi is None
        ):
            raise ValueError("Depressurization requires user-specified target_o2_pct and target_pressure_psi.")
        if self.kind == "inert_gas" and (self.target_o2_pct is None or self.inert_species is None):
            raise ValueError("Inert gas requires user-specified target_o2_pct and inert_species.")
        if self.kind == "gravity_shift" and self.target_gravity_g is None:
            raise ValueError("Gravity shift requires a user-specified target_gravity_g.")
        return self


class DigitalTwinSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline: BaselineConfig
    intervention: InterventionConfig
    duration_seconds: float = Field(default=60, gt=0, le=3600)
