from __future__ import annotations

from typing import Any

from src.catalogue import compute_scientific_simulation, load_catalogue, rank_studies


def _catalogue_context(scenario: dict[str, Any]) -> dict[str, Any]:
    oxygen = scenario.get("oxygen_pct")
    pressure_psi = scenario.get("pressure_psi")
    pressure_atm = scenario.get("pressure_atm")
    if pressure_psi is None and isinstance(pressure_atm, (int, float)):
        pressure_psi = float(pressure_atm) * 14.7
    airflow = scenario.get("airflow_cms", scenario.get("airflow_cm_s"))
    gravity = scenario.get("gravity", "Unknown")
    if gravity == "Unknown" and isinstance(scenario.get("gravity_g"), (int, float)):
        gravity_g = float(scenario["gravity_g"])
        gravity = (
            "Microgravity" if gravity_g == 0 else
            "Lunar partial gravity" if abs(gravity_g - 0.166) < 0.03 else
            "Mars partial gravity" if abs(gravity_g - 0.376) < 0.04 else
            "Earth gravity"
        )
    rank_input = {
        "mission": str(scenario.get("mission", "Decision support scenario"))[:120],
        "gravity": gravity,
        "oxygen_pct": oxygen,
        "pressure_atm": pressure_psi / 14.7 if isinstance(pressure_psi, (int, float)) else pressure_atm,
        "airflow_cm_s": airflow,
        "material": str(scenario.get("material", ""))[:200],
        "pillar": scenario.get("pillar", "Any pillar"),
    }

    ranked = rank_studies(load_catalogue(), rank_input)
    relevance = [
        {
            "psi_id": item["psi_id"],
            "name": item["short_name"],
            "match_score": item["match_score"],
            "evidence_coverage": item["evidence_coverage"],
            "source_url": item["source_url"],
            "doi": item.get("doi"),
            "local_data_status": item.get("local_data_status"),
            "interpretation": "Catalogue evidence similarity only; not a safety rating or fire prediction.",
        }
        for item in ranked[:5]
    ]

    surrogate = None
    if (
        isinstance(oxygen, (int, float))
        and isinstance(pressure_psi, (int, float))
        and isinstance(airflow, (int, float))
        and isinstance(scenario.get("gravity_g"), (int, float))
    ):
        try:
            simulation = compute_scientific_simulation(
                float(oxygen),
                float(pressure_psi),
                float(airflow),
                float(scenario["gravity_g"]),
                str(scenario.get("material", "generic material")),
            )
        except ValueError:
            surrogate = {
                "status": "not_computed",
                "interpretation": "Scenario values were outside the screening model bounds.",
            }
        else:
            surrogate = {
                "status": "computed",
                "validated": False,
                "estimated_moc_pct": simulation["metrics"]["estimated_moc_pct"],
                "flammability_index": simulation["metrics"]["flammability_index"],
                "regime_classification": simulation["metrics"]["regime_classification"],
                "model": simulation["model"],
                "interpretation": "Code-defined screening surrogate only; not measured, calibrated, or an operational limit.",
            }
    active_scenario = {
        key: value
        for key, value in scenario.items()
        if key not in {"telemetry_state", "ml_state", "digital_twin_state", "integration_warnings"}
    }
    return {
        "scenario": active_scenario,
        "catalogue_relevance": relevance,
        "physics_surrogate": surrogate,
        "telemetry_state": scenario.get("telemetry_state"),
        "ml_state": scenario.get("ml_state"),
        "digital_twin_state": scenario.get("digital_twin_state"),
        "integration_warnings": scenario.get("integration_warnings", []),
    }


def aggregate_system_state(
    scenario: dict[str, Any],
    telemetry: dict[str, Any] | None,
    ml_results: dict[str, Any] | None,
    twin_results: dict[str, Any] | None,
    integration_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Combine caller-provided subsystem snapshots with server-calculated catalogue context."""
    return _catalogue_context(
        {
            "mission": scenario.get("mission", "Decision support scenario"),
            **scenario,
            "telemetry_state": telemetry,
            "ml_state": ml_results,
            "digital_twin_state": twin_results,
            "integration_warnings": integration_warnings or [],
        }
    )
