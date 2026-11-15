from __future__ import annotations

from typing import Any, Literal


SAFETY_DISCLAIMER = (
    "EXPLORATORY SIMULATION ONLY. Do not use for operational spacecraft hardware actuation. "
    "This boundary-condition scenario is not a validated fire, extinction, or safety prediction."
)

SCIENTIFIC_REFERENCES = [
    "PSI-25 BASS-II",
    "PSI-69 FLEX",
    "PSI-98 SAFFIRE-I",
]

ASSUMPTIONS_AND_UNCERTAINTY = [
    "The local repository contains PSI catalogue records, not the numerical BASS-II, FLEX, or SAFFIRE test tables; these references provide research context and did not calibrate this simulator.",
    "Oxygen, pressure, and gravity targets are user-specified scenario boundary conditions. Transitions use linear interpolation and are not experimental response rates.",
    "The inert-gas scenario assumes a well-mixed atmosphere and is not validated for complex spacecraft geometries; ramps longer than the comparison duration remain partial.",
    "Ventilation cutoff sets the displayed airflow boundary condition to zero; heat-transfer, oxygen-consumption, and flame-blowoff equations are not modeled.",
    "For inert-gas scenarios, the user supplies the target oxygen concentration. The species is recorded for context only; CO2/helium effectiveness, radiative extinction, and an MOC threshold are not estimated.",
    "Inert-gas scenarios hold total pressure at the baseline value as a user-visible well-mixed, pressure-regulated assumption; gas injection, exhaust, and pressure transients are not modeled.",
    "Gravity changes are boundary-condition labels only; flame shape, convection, diffusion, and heat-transfer responses are not calculated.",
    "Temperature (K) and flame volume (m^3) are unchanged pass-through context when supplied, and null when unknown; they are not predicted outcomes.",
    "No numeric uncertainty margin or confidence interval is available because this model has no calibrated residuals or local intervention measurements.",
    "The simulator issues no commands and does not model sensors, actuators, cabin geometry, fuel properties, or transient combustion chemistry.",
]


def _interpolate(start: float, end: float, time_seconds: float, transition_seconds: float) -> float:
    fraction = min(1.0, time_seconds / transition_seconds)
    return start + (end - start) * fraction


def _trajectory_point(
    time_seconds: float,
    *,
    temp_k: float | None,
    flame_volume: float | None,
    o2_pct: float,
    pressure_psi: float,
    airflow_cms: float,
    gravity_g: float,
) -> dict[str, float | None]:
    return {
        "time": round(time_seconds, 6),
        "temp_k": temp_k,
        "flame_volume": flame_volume,
        "o2_pct": round(o2_pct, 6),
        "pressure_psi": round(pressure_psi, 6),
        "airflow_cms": round(airflow_cms, 6),
        "gravity_g": round(gravity_g, 6),
    }


def simulate_intervention(
    baseline_config: dict[str, Any],
    intervention_config: dict[str, Any],
    time_steps: int = 60,
    duration_seconds: float = 60,
) -> dict[str, Any]:
    """Compare explicit environment boundary conditions without predicting fire response."""
    if not isinstance(time_steps, int) or isinstance(time_steps, bool) or not 2 <= time_steps <= 1000:
        raise ValueError("time_steps must be an integer between 2 and 1000.")
    if not isinstance(duration_seconds, (int, float)) or isinstance(duration_seconds, bool) or duration_seconds <= 0:
        raise ValueError("duration_seconds must be a positive number.")

    kind: Literal["ventilation_cutoff", "depressurization", "inert_gas", "gravity_shift"] = intervention_config["kind"]
    transition_seconds = float(intervention_config.get("transition_seconds", duration_seconds))
    if transition_seconds <= 0:
        raise ValueError("transition_seconds must be positive.")

    baseline_o2 = float(baseline_config["oxygen_pct"])
    baseline_pressure = float(baseline_config["pressure_psi"])
    baseline_airflow = float(baseline_config["airflow_cms"])
    baseline_gravity = float(baseline_config["gravity_g"])
    temp_k = baseline_config.get("temp_k")
    flame_volume = baseline_config.get("flame_volume_m3")

    target_o2_value = intervention_config.get("target_o2_pct")
    target_pressure_value = intervention_config.get("target_pressure_psi")
    target_gravity_value = intervention_config.get("target_gravity_g")
    target_o2 = float(target_o2_value) if target_o2_value is not None else baseline_o2
    target_pressure = (
        float(target_pressure_value) if target_pressure_value is not None else baseline_pressure
    )
    target_gravity = (
        float(target_gravity_value) if target_gravity_value is not None else baseline_gravity
    )
    if kind in {"depressurization", "inert_gas"} and target_o2 > baseline_o2:
        raise ValueError("This scenario only supports an oxygen target at or below baseline.")
    if kind == "depressurization" and target_pressure > baseline_pressure:
        raise ValueError("Depressurization target pressure must not exceed baseline pressure.")

    baseline_trajectory: list[dict[str, float | None]] = []
    intervention_trajectory: list[dict[str, float | None]] = []
    for index in range(time_steps):
        time_seconds = duration_seconds * index / (time_steps - 1)
        baseline_trajectory.append(
            _trajectory_point(
                time_seconds,
                temp_k=temp_k,
                flame_volume=flame_volume,
                o2_pct=baseline_o2,
                pressure_psi=baseline_pressure,
                airflow_cms=baseline_airflow,
                gravity_g=baseline_gravity,
            )
        )

        o2_pct = baseline_o2
        pressure_psi = baseline_pressure
        airflow_cms = baseline_airflow
        gravity_g = baseline_gravity

        if kind == "ventilation_cutoff":
            airflow_cms = 0.0
        elif kind == "depressurization":
            o2_pct = _interpolate(baseline_o2, target_o2, time_seconds, transition_seconds)
            pressure_psi = _interpolate(baseline_pressure, target_pressure, time_seconds, transition_seconds)
        elif kind == "inert_gas":
            o2_pct = _interpolate(baseline_o2, target_o2, time_seconds, transition_seconds)
        elif kind == "gravity_shift":
            gravity_g = _interpolate(baseline_gravity, target_gravity, time_seconds, transition_seconds)
        else:
            raise ValueError(f"Unsupported intervention kind: {kind}")

        intervention_trajectory.append(
            _trajectory_point(
                time_seconds,
                temp_k=temp_k,
                flame_volume=flame_volume,
                o2_pct=o2_pct,
                pressure_psi=pressure_psi,
                airflow_cms=airflow_cms,
                gravity_g=gravity_g,
            )
        )

    return {
        "model": {
            "name": "Boundary-condition scenario interpolator",
            "version": "1.0.0",
            "validated": False,
            "calibrated": False,
            "interpretation": "Displays user-specified environment trajectories only; it does not predict fire behavior or suppressant performance.",
        },
        "baseline_trajectory": baseline_trajectory,
        "intervention_trajectory": intervention_trajectory,
        "assumptions_and_uncertainty": ASSUMPTIONS_AND_UNCERTAINTY,
        "scientific_references": SCIENTIFIC_REFERENCES,
        "safety_disclaimer": SAFETY_DISCLAIMER,
    }
