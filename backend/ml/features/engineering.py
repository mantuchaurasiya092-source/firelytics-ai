from __future__ import annotations

import math
import re
import statistics
from collections import defaultdict
from typing import Any, Mapping, Sequence

from ml.datasets.registry import unit_for_column
from ml.preprocessing.pipeline import numeric_or_missing


_TELEMETRY_CHANNELS = (
    "DustTrakAMeasurement(MgPerM3)",
    "DustTrakBMeasurement(MgPerM3)",
    "PTrakMeasurement(PtPerCC)",
    "DustTrakAAnalogMeasurement(Volts)",
    "DustTrakBAnalogMeasurement(Volts)",
    "GasPlumeTemperature(DegC)",
    "MFCTemperature(DegC)",
    "SampleResistance(Ohms)",
    "LFEFlowRate[AT08](SCCM)",
    "MFCMassFlowRate(LPM)",
    "MFCAnalogFlowRate(LPM)",
    "MFCPressure(PSIA)",
    "GN2MainPressure[PN02](PSIA)",
    "GN2RegulatedPressure[PN12](PSIG)",
    "VacuumPressure[VR04](PSIA)",
    "DriveSidePressure[BN02](PSIA)",
    "SampleSidePressure[AT20](PSIA)",
)

_TARGET_OR_LABEL_FIELDS = {
    "ExpectedBand",
    "ObservedBand",
    "RelativeCyclePhase",
    "ExceptionIndicator",
    "MixedBandIndicator",
    "DuplicateCycleIndicator",
    "DuplicateRowCount",
}


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _time_value(row: Mapping[str, Any], preferred: str) -> float | None:
    value = numeric_or_missing(row.get(preferred))
    if value is not None:
        return value
    for fallback in ("ElapsedTestTime(Secs)", "Time"):
        value = numeric_or_missing(row.get(fallback))
        if value is not None:
            return value
    return None


def engineer_telemetry_features(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_col: str = "RunID",
    time_col: str = "ElapsedTestTime(Secs)",
    rolling_window: int = 5,
) -> dict[str, Any]:
    """Create per-run, strictly past-only rolling features from local telemetry rows.

    The output row at time t uses measurements with timestamps strictly earlier than t.
    Rows with no valid prior measurement retain null feature values; -999 sentinels are
    treated as missing and no interpolation is performed.
    """
    if rolling_window < 2:
        raise ValueError("rolling_window must be at least 2.")
    grouped: dict[str, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
    for index, row in enumerate(rows):
        run_id = row.get(group_col)
        if run_id is None or not str(run_id).strip():
            raise ValueError(f"Every telemetry row must have a non-empty {group_col}.")
        grouped[str(run_id).strip()].append((index, row))

    output: list[dict[str, Any]] = []
    feature_units: dict[str, str] = {"time_s": "s"}
    for channel in _TELEMETRY_CHANNELS:
        if any(channel in row for row in rows):
            name = _safe_name(channel)
            unit = unit_for_column(channel)
            if unit is None:
                raise ValueError(f"No source unit is registered for telemetry channel {channel!r}.")
            feature_units.update(
                {
                    f"past_{name}_last": unit,
                    f"past_{name}_mean": unit,
                    f"past_{name}_std": unit,
                    f"past_{name}_slope_per_s": f"{unit}/s",
                }
            )
    feature_units.update(
        {
            "past_dusttrak_a_to_b_mass_ratio": "dimensionless",
            "past_ptrak_to_dusttrak_a": "(particles/cm³)/(mg/m³)",
        }
    )

    for run_id in sorted(grouped):
        indexed = sorted(
            grouped[run_id],
            key=lambda item: (
                _time_value(item[1], time_col)
                if _time_value(item[1], time_col) is not None
                else float("inf"),
                numeric_or_missing(item[1].get("_source_row")) or item[0],
                item[0],
            ),
        )
        history: list[tuple[float | None, Mapping[str, Any]]] = []
        for original_index, row in indexed:
            current_time = _time_value(row, time_col)
            prior = history[-rolling_window:]
            features: dict[str, Any] = {
                "RunID": run_id,
                "source_index": original_index,
                "source_row": row.get("_source_row"),
                "time_s": current_time,
            }
            prior_values: dict[str, float | None] = {}
            for channel in _TELEMETRY_CHANNELS:
                if channel not in row:
                    continue
                channel_name = _safe_name(channel)
                valid = [
                    (numeric_or_missing(previous_row.get(channel)), previous_time)
                    for previous_time, previous_row in prior
                ]
                valid = [(value, timestamp) for value, timestamp in valid if value is not None]
                last = valid[-1][0] if valid else None
                prior_values[channel] = last
                values = [value for value, _timestamp in valid]
                slope = None
                if len(valid) >= 2:
                    (older_value, older_time), (newer_value, newer_time) = valid[-2:]
                    if older_time is not None and newer_time is not None and newer_time > older_time:
                        slope = (newer_value - older_value) / (newer_time - older_time)
                features[f"past_{channel_name}_last"] = last
                features[f"past_{channel_name}_mean"] = (
                    statistics.fmean(values) if values else None
                )
                features[f"past_{channel_name}_std"] = (
                    statistics.pstdev(values) if len(values) > 1 else (0.0 if values else None)
                )
                features[f"past_{channel_name}_slope_per_s"] = slope

            dust_a = prior_values.get("DustTrakAMeasurement(MgPerM3)")
            dust_b = prior_values.get("DustTrakBMeasurement(MgPerM3)")
            ptrak = prior_values.get("PTrakMeasurement(PtPerCC)")
            features["past_dusttrak_a_to_b_mass_ratio"] = (
                dust_a / dust_b if dust_a is not None and dust_b not in (None, 0) else None
            )
            features["past_ptrak_to_dusttrak_a"] = (
                ptrak / dust_a if ptrak is not None and dust_a not in (None, 0) else None
            )
            output.append(features)
            history.append((current_time, row))

    return {
        "rows": output,
        "feature_units": feature_units,
        "source_row_count": len(rows),
        "group_count": len(grouped),
        "causal_window": "strictly earlier rows from the same RunID; current and future sensor values excluded",
        "missing_handling": "blank and -999 values remain null; no cross-gap imputation",
        "provenance_columns": ["RunID", "source_index", "source_row", "time_s"],
    }


def engineer_cycle_features(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_col: str = "RunID",
    phase_period: int | None = None,
    phase_origin: int = 0,
) -> dict[str, Any]:
    """Create causal cycle-index/time features without using any archived target labels.

    Optional sinusoidal phase terms require a phase period and origin fixed from an
    independent protocol before inspecting the target labels. The exception task should
    leave them unset unless that protocol exists.
    """
    if phase_period is not None and phase_period < 2:
        raise ValueError("phase_period must be at least 2 when supplied.")
    grouped: dict[str, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
    for index, row in enumerate(rows):
        run_id = row.get(group_col)
        if run_id is None or not str(run_id).strip():
            raise ValueError(f"Every cycle row must have a non-empty {group_col}.")
        grouped[str(run_id).strip()].append((index, row))

    output: list[dict[str, Any]] = []
    units = {
        "cycle_index": "cycle index",
        "cycle_gap_from_previous": "cycles",
        "elapsed_seconds_since_previous": "s",
    }
    if phase_period is not None:
        units["cycle_phase_sin"] = "dimensionless"
        units["cycle_phase_cos"] = "dimensionless"

    for run_id in sorted(grouped):
        ordered = sorted(
            grouped[run_id],
            key=lambda item: (
                numeric_or_missing(item[1].get("Cycle"))
                if numeric_or_missing(item[1].get("Cycle")) is not None
                else float("inf"),
                item[0],
            ),
        )
        previous_cycle: float | None = None
        previous_time: float | None = None
        for source_index, row in ordered:
            cycle = numeric_or_missing(row.get("Cycle"))
            time_seconds = numeric_or_missing(row.get("FirstTimestampSeconds"))
            gap = cycle - previous_cycle if cycle is not None and previous_cycle is not None else None
            elapsed = (
                time_seconds - previous_time
                if time_seconds is not None
                and previous_time is not None
                and time_seconds >= previous_time
                else None
            )
            features: dict[str, Any] = {
                "RunID": run_id,
                "source_index": source_index,
                "cycle_index": cycle,
                "cycle_gap_from_previous": gap,
                "elapsed_seconds_since_previous": elapsed,
            }
            if phase_period is not None and cycle is not None:
                angle = 2 * math.pi * ((cycle - phase_origin) % phase_period) / phase_period
                features["cycle_phase_sin"] = math.sin(angle)
                features["cycle_phase_cos"] = math.cos(angle)
            output.append(features)
            previous_cycle = cycle
            previous_time = time_seconds

    return {
        "rows": output,
        "feature_units": units,
        "source_row_count": len(rows),
        "group_count": len(grouped),
        "excluded_target_fields": sorted(_TARGET_OR_LABEL_FIELDS),
        "phase_terms_enabled": phase_period is not None,
        "phase_terms_warning": (
            "Only use phase_period/phase_origin fixed independently of target outcomes."
            if phase_period is not None
            else None
        ),
    }
