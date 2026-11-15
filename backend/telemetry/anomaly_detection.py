from __future__ import annotations

import math
import statistics
from collections import defaultdict, deque
from typing import Any


RULE_O2_DROP_PERCENT_POINTS = 2.0
RULE_TEMP_RISE_C_PER_SECOND = 50.0
RULE_AIRFLOW_FAILURE_CM_S = 0.5
ROLLING_Z_THRESHOLD = 3.0
ROLLING_WINDOW = 60
MINIMUM_ROLLING_SAMPLES = 8

_UNITS = {
    "O2_pct": "%",
    "PO2_psi": "psi",
    "pressure_psi": "psi",
    "temp_c": "°C",
    "airflow_cms": "cm/s",
    "smoke_mg_m3": "mg/m³",
    "gravity_g": "g",
}


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class TelemetryAnomalyDetector:
    """Transparent threshold and rolling-z-score rules; outputs are not flight alarms."""

    def __init__(self) -> None:
        self._history: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=ROLLING_WINDOW)
        )
        self._alert_sequence = 0

    def reset(self) -> None:
        self._history.clear()
        self._alert_sequence = 0

    def _alert(
        self,
        frame: dict[str, Any],
        *,
        what_changed: str,
        trigger_variables: list[str],
        severity: str,
        supporting_observations: list[str],
        detection_method: str,
    ) -> dict[str, Any]:
        self._alert_sequence += 1
        method_label = "Rule-based" if detection_method == "rule_based" else "Rolling z-score"
        return {
            "alert_id": f"TEL-{self._alert_sequence:06d}",
            "timestamp": frame["timestamp"],
            "what_changed": f"{method_label}: {what_changed}",
            "trigger_variables": trigger_variables,
            "severity": severity,
            "supporting_observations": supporting_observations,
            "source_mode": frame["source_mode"],
        }

    def evaluate(
        self, frame: dict[str, Any], previous_frame: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        current_o2 = _finite(frame.get("O2_pct"))
        previous_o2 = _finite(previous_frame.get("O2_pct")) if previous_frame else None
        if current_o2 is not None and previous_o2 is not None:
            drop = previous_o2 - current_o2
            if drop > RULE_O2_DROP_PERCENT_POINTS:
                alerts.append(self._alert(
                    frame,
                    what_changed="Oxygen concentration decreased by more than 2 percentage points.",
                    trigger_variables=["O2_pct"],
                    severity="CAUTION",
                    supporting_observations=[
                        f"Previous O2_pct={previous_o2:.3f}%; current O2_pct={current_o2:.3f}%; "
                        f"drop={drop:.3f} percentage points (rule > {RULE_O2_DROP_PERCENT_POINTS:.1f})."
                    ],
                    detection_method="rule_based",
                ))

        current_temp = _finite(frame.get("temp_c"))
        previous_temp = _finite(previous_frame.get("temp_c")) if previous_frame else None
        if current_temp is not None and previous_temp is not None:
            elapsed = _finite(frame.get("source_elapsed_s"))
            previous_elapsed = _finite(previous_frame.get("source_elapsed_s")) if previous_frame else None
            delta_seconds = elapsed - previous_elapsed if elapsed is not None and previous_elapsed is not None else 1.0
            if delta_seconds > 0:
                rise_rate = (current_temp - previous_temp) / delta_seconds
                if rise_rate > RULE_TEMP_RISE_C_PER_SECOND:
                    alerts.append(self._alert(
                        frame,
                        what_changed="Temperature rose faster than the configured rate-change rule.",
                        trigger_variables=["temp_c"],
                        severity="CRITICAL",
                        supporting_observations=[
                            f"Previous temp_c={previous_temp:.3f}°C; current temp_c={current_temp:.3f}°C; "
                            f"rise={rise_rate:.3f}°C/s (rule > {RULE_TEMP_RISE_C_PER_SECOND:.1f}°C/s)."
                        ],
                        detection_method="rule_based",
                    ))

        current_airflow = _finite(frame.get("airflow_cms"))
        previous_airflow = _finite(previous_frame.get("airflow_cms")) if previous_frame else None
        if (
            current_airflow is not None
            and previous_airflow is not None
            and previous_airflow > RULE_AIRFLOW_FAILURE_CM_S
            and current_airflow <= RULE_AIRFLOW_FAILURE_CM_S
        ):
            alerts.append(self._alert(
                frame,
                what_changed="Airflow fell from above the configured minimum to near zero.",
                trigger_variables=["airflow_cms"],
                severity="CRITICAL",
                supporting_observations=[
                    f"Previous airflow_cms={previous_airflow:.3f} cm/s; current airflow_cms="
                    f"{current_airflow:.3f} cm/s (failure rule <= {RULE_AIRFLOW_FAILURE_CM_S:.1f} cm/s)."
                ],
                detection_method="rule_based",
            ))

        for field, unit in _UNITS.items():
            value = _finite(frame.get(field))
            if value is None:
                continue
            prior = self._history[field]
            if len(prior) >= MINIMUM_ROLLING_SAMPLES:
                mean = statistics.fmean(prior)
                standard_deviation = statistics.pstdev(prior)
                if standard_deviation > 0:
                    z_score = abs(value - mean) / standard_deviation
                    if z_score > ROLLING_Z_THRESHOLD:
                        alerts.append(self._alert(
                            frame,
                            what_changed=f"{field} deviated from its recent rolling baseline.",
                            trigger_variables=[field],
                            severity="CAUTION",
                            supporting_observations=[
                                f"{field}={value:.4g} {unit}; prior rolling mean={mean:.4g} {unit}; "
                                f"standard deviation={standard_deviation:.4g} {unit}; "
                                f"|z|={z_score:.3f} (> {ROLLING_Z_THRESHOLD:.1f})."
                            ],
                            detection_method="rolling_z_score",
                        ))
            prior.append(value)
        return alerts
