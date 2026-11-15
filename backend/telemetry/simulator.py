from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Literal


ScenarioName = Literal[
    "nominal_operations",
    "gradual_overheat",
    "sudden_temperature_spike",
    "abnormal_oxygen",
    "airflow_failure",
    "sensor_noise_spike",
    "communication_interruption",
]

SCENARIOS: tuple[ScenarioName, ...] = (
    "nominal_operations",
    "gradual_overheat",
    "sudden_temperature_spike",
    "abnormal_oxygen",
    "airflow_failure",
    "sensor_noise_spike",
    "communication_interruption",
)

TELEMETRY_FIELDS = (
    "O2_pct",
    "PO2_psi",
    "pressure_psi",
    "temp_c",
    "airflow_cms",
    "smoke_mg_m3",
    "gravity_g",
)


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class SyntheticTelemetryGenerator:
    """Generate an illustrative stream; no value is sourced from NASA telemetry."""

    def __init__(
        self,
        scenario: ScenarioName = "nominal_operations",
        *,
        seed: int = 0,
        start_time: datetime | None = None,
    ) -> None:
        if scenario not in SCENARIOS:
            raise ValueError(f"Unsupported synthetic scenario: {scenario!r}.")
        self.scenario = scenario
        self.seed = seed
        self.start_time = start_time or datetime.now(timezone.utc)

    def generate(self, frame_index: int) -> dict[str, Any]:
        if frame_index < 0:
            raise ValueError("frame_index must be non-negative.")

        rng = random.Random(self.seed + frame_index)
        elevated_noise = self.scenario == "sensor_noise_spike" and frame_index >= 5
        noise_scale = 1.0 if elevated_noise else 0.04

        oxygen = 21.0 + rng.gauss(0.0, 0.025 * noise_scale)
        pressure = 14.7 + rng.gauss(0.0, 0.005 * noise_scale)
        temperature = 22.0 + 0.02 * frame_index + 0.15 * math.sin(frame_index / 12)
        temperature += rng.gauss(0.0, 0.08 * noise_scale)
        airflow = 10.0 + 0.3 * math.sin(frame_index / 8) + rng.gauss(0.0, 0.1 * noise_scale)
        aerosol = max(0.0, 0.02 + rng.gauss(0.0, 0.002 * noise_scale))
        gravity = 0.0001

        if self.scenario == "gradual_overheat" and frame_index >= 5:
            temperature += 0.35 * (frame_index - 4)
        elif self.scenario == "sudden_temperature_spike" and frame_index >= 5:
            temperature += 65.0
        elif self.scenario == "abnormal_oxygen" and frame_index >= 5:
            oxygen = max(0.0, oxygen - 2.5 * (frame_index - 4))
        elif self.scenario == "airflow_failure" and frame_index >= 5:
            airflow = 0.0
        elif self.scenario == "sensor_noise_spike" and frame_index >= 5:
            oxygen = min(100.0, max(0.0, oxygen + rng.gauss(0.0, 0.9)))
            temperature += rng.gauss(0.0, 5.0)
            airflow = max(0.0, airflow + rng.gauss(0.0, 2.0))
            aerosol = max(0.0, aerosol + rng.gauss(0.0, 0.05))

        noise_profile = "elevated_synthetic_noise" if elevated_noise else "nominal_synthetic_noise"
        values: dict[str, float | None] = {
            "O2_pct": oxygen,
            "PO2_psi": oxygen / 100.0 * pressure,
            "pressure_psi": pressure,
            "temp_c": temperature,
            "airflow_cms": airflow,
            "smoke_mg_m3": aerosol,
            "gravity_g": gravity,
        }
        if self.scenario == "communication_interruption" and frame_index % 5 == 4:
            values = {name: None for name in TELEMETRY_FIELDS}
            noise_profile = "synthetic_packet_gap"

        return {
            "frame_id": frame_index + 1,
            "timestamp": _isoformat(self.start_time + timedelta(seconds=frame_index)),
            **values,
            "sensor_noise_profile": noise_profile,
            "source_mode": "SYNTHETIC",
            "scenario": self.scenario,
            "source_timestamp": None,
            "source_elapsed_s": float(frame_index),
            "source_measurements": {},
        }
