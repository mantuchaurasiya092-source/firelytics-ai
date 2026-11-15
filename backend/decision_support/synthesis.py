from __future__ import annotations

from typing import Any


def _alerts(state: dict[str, Any]) -> list[dict[str, Any]]:
    telemetry = state.get("telemetry_state")
    if not isinstance(telemetry, dict):
        return []
    alerts = telemetry.get("active_anomalies", telemetry.get("alerts", []))
    if not isinstance(alerts, list):
        return []
    return [item for item in alerts[:200] if isinstance(item, dict)]


def _ml_summary(state: dict[str, Any]) -> dict[str, Any]:
    supplied = state.get("ml_state")
    if not isinstance(supplied, dict):
        return {
            "status": "not_provided",
            "prediction": None,
            "validation_metrics": None,
            "provenance": "No prediction or model metrics were supplied.",
        }
    prediction = supplied.get("prediction")
    metrics = supplied.get("validation_metrics")
    return {
        "status": "caller_provided",
        "prediction": prediction if isinstance(prediction, dict) else None,
        "validation_metrics": metrics if isinstance(metrics, dict) else None,
        "models": supplied.get("models") if isinstance(supplied.get("models"), list) else [],
        "training_performed": supplied.get("training_performed"),
        "runid_leakage_check_passed": supplied.get("runid_leakage_check_passed"),
        "model_id": supplied.get("model_id"),
        "provenance": (
            "Passed through from the request; this endpoint does not execute inference or independently verify predictions/metrics."
        ),
    }


def _intervention_summary(state: dict[str, Any]) -> dict[str, Any]:
    supplied = state.get("digital_twin_state")
    if not isinstance(supplied, dict):
        return {
            "status": "not_provided",
            "baseline_trajectory": [],
            "intervention_trajectory": [],
            "interpretation": "No digital-twin result was supplied; no intervention was simulated by this brief.",
        }
    baseline = supplied.get("baseline_trajectory")
    intervention = supplied.get("intervention_trajectory")
    return {
        "status": "caller_provided",
        "baseline_trajectory": baseline[:1000] if isinstance(baseline, list) else [],
        "intervention_trajectory": intervention[:1000] if isinstance(intervention, list) else [],
        "assumptions_and_uncertainty": supplied.get("assumptions_and_uncertainty", []),
        "safety_disclaimer": supplied.get("safety_disclaimer"),
        "interpretation": (
            "Boundary-condition trajectories passed through from the request; not predicted fire or suppressant outcomes."
        ),
    }


def generate_research_brief(
    aggregated_state: dict[str, Any],
    rag_context: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic evidence-linked brief; never ask an LLM to make safety decisions."""
    telemetry = aggregated_state.get("telemetry_state")
    alerts = _alerts(aggregated_state)
    telemetry_summary = {
        "status": "not_provided" if not isinstance(telemetry, dict) else "caller_provided",
        "source_mode": telemetry.get("data_label", telemetry.get("source_mode")) if isinstance(telemetry, dict) else None,
        "alerts": alerts,
        "alert_count": len(alerts),
        "interpretation": (
            "Caller-provided telemetry snapshot; alerts are rule/statistical triggers, not flight alarms or safety decisions."
            if isinstance(telemetry, dict)
            else "No telemetry snapshot was supplied."
        ),
    }

    gaps: list[dict[str, Any]] = []
    for item in aggregated_state.get("catalogue_relevance", []):
        local_status = str(item.get("local_data_status") or "")
        if local_status and any(term in local_status.lower() for term in ("catalog", "not locally", "unavailable", "metadata")):
            gaps.append(
                {
                    "psi_id": item["psi_id"],
                    "gap": local_status,
                    "source_url": item["source_url"],
                }
            )
    if not gaps:
        gaps.append(
            {
                "psi_id": None,
                "gap": "This request does not establish that the specific experiment tables needed to validate this scenario are available locally.",
                "source_url": None,
            }
        )

    citations = [
        {
            key: value
            for key, value in citation.items()
            if key in {"chunk_id", "psi_id", "title", "doi", "source_path_or_url", "relevance_score", "excerpt", "epistemic_tier"}
        }
        for citation in rag_context[:8]
    ]
    scenario = aggregated_state["scenario"]
    calculated = aggregated_state.get("physics_surrogate")
    measured = {
        "scenario_inputs": {
            key: scenario.get(key)
            for key in ("mission", "oxygen_pct", "pressure_psi", "pressure_atm", "airflow_cms", "airflow_cm_s", "gravity_g", "material")
            if key in scenario
        },
        "telemetry_alerts": alerts,
        "status": "Values and alerts are caller-provided; none are independently measured or verified by this synthesis endpoint.",
    }
    calculated_surrogates = {
        "catalogue_relevance": aggregated_state.get("catalogue_relevance", []),
        "physics": calculated,
        "interpretation": "Catalogue matching and physics metrics are project calculations; neither is a validated safety assessment.",
    }
    return {
        "summary": (
            "Evidence-linked research brief generated deterministically from the supplied scenario, local catalogue, and retrieved context. "
            "It makes no safety decision or operational recommendation."
        ),
        "active_scenario_context": scenario,
        "relevance_ranking": aggregated_state.get("catalogue_relevance", []),
        "anomaly_analysis": telemetry_summary,
        "ml_insights": _ml_summary(aggregated_state),
        "intervention_comparison": _intervention_summary(aggregated_state),
        "evidence_gaps": gaps,
        "supporting_citations": citations,
        "epistemic_separation": {
            "measured_data": measured,
            "calculated_surrogates": calculated_surrogates,
            "generated_llm_suggestions": {
                "status": "not_generated",
                "items": [],
                "reason": "No LLM was invoked; ungrounded recommendations and invented safety decisions are excluded.",
            },
        },
        "integration_warnings": aggregated_state.get("integration_warnings", []),
        "safety_disclaimer": (
            "Research support only. No fire-safety determination, operational recommendation, actuator command, "
            "or flight decision is produced. Validate all evidence against its cited primary source."
        ),
    }
