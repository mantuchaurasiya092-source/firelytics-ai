from __future__ import annotations

from fastapi import APIRouter, HTTPException

from digital_twin.schemas import DigitalTwinSimulationRequest
from digital_twin.simulator import simulate_intervention

router = APIRouter(tags=["exploratory fire mitigation digital twin"])


@router.post("/digital-twin/simulate")
@router.post("/api/digital-twin/simulate")
def simulate_digital_twin(request: DigitalTwinSimulationRequest):
    try:
        return simulate_intervention(
            request.baseline.model_dump(),
            request.intervention.model_dump(),
            duration_seconds=request.duration_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
