from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ml.models.runtime import (
    load_model_artifact,
    load_model_registry,
    predict_with_artifact,
)
from ml.datasets.registry import (
    assess_candidate_tasks,
    build_dataset_registry,
    get_dataset_quality,
)


router = APIRouter(tags=["local dataset discovery and quality"])


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(pattern=r"^[a-z0-9_]{1,64}$")
    features: dict[str, float | None]
    feature_units: dict[str, str]


@router.get("/ml/datasets")
@router.get("/api/ml/datasets")
def ml_datasets() -> dict[str, Any]:
    """Return inspected local datasets, provenance, schemas, and availability."""
    return build_dataset_registry()


@router.get("/ml/tasks")
@router.get("/api/ml/tasks")
def ml_tasks() -> dict[str, Any]:
    """Return evidence-grounded feasibility assessments for the six candidate tasks."""
    return {
        "candidate_task_count": 6,
        "tasks": assess_candidate_tasks(),
        "interpretation": (
            "Feasibility is scoped to the exact local labels described for each task. "
            "Phase 3 models, when present, apply only to archived PSI-101 ObservedBand "
            "labels and are not fire, ignition, extinction, or smoke-versus-dust classifiers."
        ),
    }


@router.get("/ml/datasets/{dataset_id}/quality")
@router.get("/api/ml/datasets/{dataset_id}/quality")
def ml_dataset_quality(dataset_id: str) -> dict[str, Any]:
    """Return observed missingness, run-level distributions, and grouped leakage audit."""
    report = get_dataset_quality(dataset_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id!r} is not registered.")
    return report


@router.get("/ml/models")
@router.get("/api/ml/models")
def ml_models() -> dict[str, Any]:
    """Return local model versions and their grouped held-out evaluation results."""
    try:
        registry = load_model_registry()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "task_id": registry["task_id"],
        "task_name": registry["task_name"],
        "target_interpretation": registry["target_interpretation"],
        "training_performed": registry["training_performed"],
        "record_count": registry["record_count"],
        "run_ids": registry["run_ids"],
        "grouped_evaluation_method": registry["grouped_evaluation_method"],
        "runid_leakage_check_passed": registry["runid_leakage_check_passed"],
        "model_artifacts_local_only": registry["model_artifacts_local_only"],
        "safety_disclaimer": registry["safety_disclaimer"],
        "models": registry["models"],
    }


@router.post("/ml/predict")
@router.post("/api/ml/predict")
def ml_predict(request: PredictionRequest) -> dict[str, Any]:
    """Predict an archived band from unit-declared, independent sensor channels."""
    try:
        artifact = load_model_artifact(request.model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    feature_schema = artifact.get("feature_schema")
    if not isinstance(feature_schema, list):
        raise HTTPException(status_code=500, detail="Model artifact has no feature schema.")
    expected_units = {
        item["name"]: item["unit"]
        for item in feature_schema
        if isinstance(item, dict) and "name" in item and "unit" in item
    }
    if set(request.features) != set(expected_units):
        raise HTTPException(
            status_code=422,
            detail="Provide every model feature key; unavailable values may be null.",
        )
    if request.feature_units != expected_units:
        raise HTTPException(
            status_code=422,
            detail="Feature units must exactly match the trained model schema.",
        )
    if not any(value is not None for value in request.features.values()):
        raise HTTPException(
            status_code=422,
            detail="At least one finite sensor feature value is required.",
        )
    try:
        prediction = predict_with_artifact(artifact, request.features)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "model_id": artifact["model_id"],
        "model_version": artifact["model_version"],
        "dataset_id": artifact["dataset_id"],
        "target_name": artifact["target_name"],
        "target_interpretation": artifact["target_interpretation"],
        "prediction": prediction,
        "grouped_evaluation_method": artifact["grouped_evaluation"]["method"],
        "runid_leakage_check_passed": artifact["grouped_evaluation"]["leakage_check_passed"],
        "safety_disclaimer": artifact["safety_disclaimer"],
    }


@router.get("/ml/explainability/{model_id}")
@router.get("/api/ml/explainability/{model_id}")
def ml_explainability(model_id: str) -> dict[str, Any]:
    """Return global feature importance and exact empirical Shapley summaries."""
    try:
        artifact = load_model_artifact(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    explanation = artifact.get("explainability")
    if not isinstance(explanation, dict):
        raise HTTPException(status_code=500, detail="Model artifact has no explainability summary.")
    return {
        "model_id": artifact["model_id"],
        "model_version": artifact["model_version"],
        "dataset_id": artifact["dataset_id"],
        "target_interpretation": artifact["target_interpretation"],
        "global_feature_importance": explanation["global_feature_importance"],
        "shap_summary": explanation["shap_summary"],
        "shap_method": explanation["method"],
        "explanation_scope": explanation["data_scope"],
        "safety_disclaimer": artifact["safety_disclaimer"],
    }
