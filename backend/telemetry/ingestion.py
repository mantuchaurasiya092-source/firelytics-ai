from __future__ import annotations

import csv
import io
import math
import re
from datetime import datetime, timezone
from typing import Any, Iterable

from ml.datasets.loader import load_psi101_raw_run


MAX_UPLOAD_BYTES = 2_000_000
MAX_UPLOAD_ROWS = 10_000
VALIDATED_PSI101_RUN_IDS = ("63", "64", "76", "84", "95", "97")

_NUMERIC_FIELDS = (
    "O2_pct",
    "PO2_psi",
    "pressure_psi",
    "temp_c",
    "airflow_cms",
    "smoke_mg_m3",
    "gravity_g",
    "aerosol_mass_mg_m3",
    "ptrak_particles_cm3",
    "sample_resistance_ohm",
    "sample_side_pressure_psia",
    "mfc_pressure_psia",
    "mfc_mass_flow_lpm",
    "lfe_flow_rate_sccm",
    "source_elapsed_s",
)
_CORE_MEASUREMENT_FIELDS = {
    "O2_pct",
    "PO2_psi",
    "pressure_psi",
    "temp_c",
    "airflow_cms",
    "smoke_mg_m3",
    "gravity_g",
}
_MEASUREMENT_FIELDS = set(_NUMERIC_FIELDS) - {"source_elapsed_s"}
_ALIASES: dict[str, str] = {}
for _canonical, _aliases in {
    "O2_pct": ("o2_pct", "oxygen_pct"),
    "PO2_psi": ("po2_psi", "oxygen_partial_pressure_psi"),
    "pressure_psi": ("pressure_psi", "cabin_pressure_psi"),
    "temp_c": ("temp_c", "temperature_c", "gasplumetemperaturedegc"),
    "airflow_cms": ("airflow_cms", "air_velocity_cm_s"),
    "smoke_mg_m3": ("smoke_mg_m3",),
    "gravity_g": ("gravity_g",),
    "aerosol_mass_mg_m3": (
        "aerosol_mass_mg_m3",
        "dusttrakamgperm3",
        "dusttrakameasurementmgperm3",
    ),
    "ptrak_particles_cm3": ("ptrak_particles_cm3", "ptrakmeasurementptpercc"),
    "sample_resistance_ohm": ("sample_resistance_ohm", "sampleresistanceohms"),
    "sample_side_pressure_psia": (
        "sample_side_pressure_psia",
        "samplesidepressureat20psia",
    ),
    "mfc_pressure_psia": ("mfc_pressure_psia", "mfcpressurepsia"),
    "mfc_mass_flow_lpm": ("mfc_mass_flow_lpm", "mfcmassflowratelpm"),
    "lfe_flow_rate_sccm": ("lfe_flow_rate_sccm", "lfeflowrateat08sccm"),
    "source_elapsed_s": ("elapsedtesttimesecs", "elapsed_s", "source_elapsed_s"),
    "source_timestamp": ("timestamp", "source_timestamp", "timestring"),
    "sensor_noise_profile": ("sensor_noise_profile",),
}.items():
    for _alias in _aliases:
        _ALIASES[re.sub(r"[^a-z0-9]", "", _alias.lower())] = _canonical


def _numeric_or_none(value: Any) -> float | None:
    if value is None or str(value).strip().lower() in {"", "na", "n/a", "nan", "null", "-999", "-999.0"}:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Telemetry value {value!r} is not numeric.") from exc
    if not math.isfinite(number):
        return None
    return number


def _timestamp_seconds(value: Any) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        numeric = float(value)
    except ValueError:
        numeric = None
    if numeric is not None:
        return numeric if math.isfinite(numeric) else None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def parse_telemetry_csv(content: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse bounded, user-provided CSV into explicit SI/domain fields."""
    if len(content.encode("utf-8")) > MAX_UPLOAD_BYTES:
        raise ValueError(f"CSV upload exceeds the {MAX_UPLOAD_BYTES}-byte limit.")
    try:
        reader = csv.DictReader(io.StringIO(content, newline=""))
        headers = reader.fieldnames or []
        if not headers or len(headers) > 128:
            raise ValueError("CSV must have a header with no more than 128 columns.")
        if any(not header or len(header) > 128 for header in headers):
            raise ValueError("CSV headers must be non-empty and at most 128 characters.")
        normalized_headers = [re.sub(r"[^a-z0-9]", "", header.lower()) for header in headers]
        if len(set(normalized_headers)) != len(normalized_headers):
            raise ValueError("CSV headers must be unique after normalization.")

        mapped: dict[str, str] = {}
        for header in headers:
            canonical = _ALIASES.get(re.sub(r"[^a-z0-9]", "", header.lower()))
            if canonical:
                if canonical in mapped:
                    raise ValueError(f"CSV has multiple columns mapping to {canonical}.")
                mapped[canonical] = header
        telemetry_columns = set(mapped) & set(_NUMERIC_FIELDS)
        if not telemetry_columns.intersection(_CORE_MEASUREMENT_FIELDS):
            raise ValueError("CSV needs at least one recognized telemetry measurement column.")

        rows: list[dict[str, Any]] = []
        has_measurement = False
        for row_number, raw in enumerate(reader, start=1):
            if row_number > MAX_UPLOAD_ROWS:
                raise ValueError(f"CSV exceeds the {MAX_UPLOAD_ROWS}-row limit.")
            if None in raw:
                raise ValueError(f"CSV row {row_number} has more values than the header.")
            if not raw or all(value is None or not value.strip() for value in raw.values()):
                continue
            parsed: dict[str, Any] = {}
            for canonical, header in mapped.items():
                value = raw.get(header)
                if canonical == "sensor_noise_profile":
                    parsed[canonical] = (value or "").strip() or "not recorded in uploaded CSV"
                elif canonical == "source_timestamp":
                    parsed[canonical] = (value or "").strip() or None
                else:
                    parsed[canonical] = _numeric_or_none(value)
                    if canonical in _CORE_MEASUREMENT_FIELDS and parsed[canonical] is not None:
                        has_measurement = True
            parsed["source_fields_available"] = [
                canonical for canonical in telemetry_columns & _MEASUREMENT_FIELDS
                if parsed.get(canonical) is not None
            ]
            rows.append(parsed)
        if not rows or not has_measurement:
            raise ValueError("CSV contains no usable numeric telemetry measurements.")
        time_origin: float | None = None
        for row in rows:
            timestamp_seconds = _timestamp_seconds(row.get("source_timestamp"))
            if timestamp_seconds is not None:
                if time_origin is None:
                    time_origin = timestamp_seconds
                if row.get("source_elapsed_s") is None:
                    row["source_elapsed_s"] = timestamp_seconds - time_origin
        return rows, headers
    except csv.Error as exc:
        raise ValueError(f"Unable to parse CSV: {exc}") from exc


def _frame_from_values(
    values: dict[str, Any],
    *,
    frame_id: int,
    timestamp: datetime,
    source_mode: str,
    source_timestamp: str | None,
    source_elapsed_s: float | None,
    source_measurements: dict[str, Any],
    source_fields_available: list[str],
    sensor_noise_profile: str,
) -> dict[str, Any]:
    return {
        "frame_id": frame_id,
        "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        **{name: values.get(name) for name in (
            "O2_pct", "PO2_psi", "pressure_psi", "temp_c", "airflow_cms", "smoke_mg_m3", "gravity_g"
        )},
        "sensor_noise_profile": sensor_noise_profile,
        "source_mode": source_mode,
        "scenario": None,
        "source_timestamp": source_timestamp,
        "source_elapsed_s": source_elapsed_s,
        "source_fields_available": source_fields_available,
        "source_measurements": source_measurements,
    }


def psi101_raw_row_to_frame(
    row: dict[str, Any], *, frame_id: int, timestamp: datetime
) -> dict[str, Any]:
    """Map only semantically compatible PSI-101 fields; never infer cabin O2/air velocity/smoke."""
    values: dict[str, Any] = {
        "O2_pct": None,
        "PO2_psi": None,
        "pressure_psi": None,
        "temp_c": _numeric_or_none(row.get("GasPlumeTemperature(DegC)")),
        "airflow_cms": None,
        "smoke_mg_m3": None,
        "gravity_g": None,
    }
    source_measurements = {
        "aerosol_mass_mg_m3": _numeric_or_none(row.get("DustTrakAMeasurement(MgPerM3)")),
        "ptrak_particles_cm3": _numeric_or_none(row.get("PTrakMeasurement(PtPerCC)")),
        "sample_resistance_ohm": _numeric_or_none(row.get("SampleResistance(Ohms)")),
        "sample_side_pressure_psia": _numeric_or_none(row.get("SampleSidePressure[AT20](PSIA)")),
        "mfc_pressure_psia": _numeric_or_none(row.get("MFCPressure(PSIA)")),
        "mfc_mass_flow_lpm": _numeric_or_none(row.get("MFCMassFlowRate(LPM)")),
        "lfe_flow_rate_sccm": _numeric_or_none(row.get("LFEFlowRate[AT08](SCCM)")),
    }
    elapsed = _numeric_or_none(row.get("ElapsedTestTime(Secs)"))
    present_channels = [
        key for key, value in {
            "temp_c": values["temp_c"],
            **source_measurements,
        }.items() if value is not None
    ]
    return _frame_from_values(
        values,
        frame_id=frame_id,
        timestamp=timestamp,
        source_mode="REPLAY",
        source_timestamp=str(row.get("TimeString") or "") or None,
        source_elapsed_s=elapsed,
        source_measurements=source_measurements,
        source_fields_available=present_channels,
        sensor_noise_profile="not recorded in PSI-101 source",
    )


def user_csv_row_to_frame(
    row: dict[str, Any], *, frame_id: int, timestamp: datetime
) -> dict[str, Any]:
    values = {name: row.get(name) for name in (
        "O2_pct", "PO2_psi", "pressure_psi", "temp_c", "airflow_cms", "smoke_mg_m3", "gravity_g"
    )}
    source_measurements = {
        name: row.get(name)
        for name in _NUMERIC_FIELDS
        if name not in values and row.get(name) is not None
    }
    return _frame_from_values(
        values,
        frame_id=frame_id,
        timestamp=timestamp,
        source_mode="REPLAY",
        source_timestamp=row.get("source_timestamp"),
        source_elapsed_s=row.get("source_elapsed_s"),
        source_measurements=source_measurements,
        source_fields_available=row.get("source_fields_available", []),
        sensor_noise_profile=row.get("sensor_noise_profile", "not recorded in uploaded CSV"),
    )


class Psi101RawReplayer:
    """Sequential one-frame-at-a-time replay from a vetted, locally present run."""

    def __init__(self, run_id: str) -> None:
        if run_id not in VALIDATED_PSI101_RUN_IDS:
            raise ValueError(f"Run {run_id!r} is not in the six reconciled PSI-101 Pyrell runs.")
        self.run_id = run_id
        self.rows = iter(load_psi101_raw_run(run_id))

    def next_frame(self, frame_id: int, timestamp: datetime) -> dict[str, Any] | None:
        row = next(self.rows, None)
        if row is None:
            return None
        return psi101_raw_row_to_frame(row, frame_id=frame_id, timestamp=timestamp)


class UserCsvReplayer:
    def __init__(self, rows: Iterable[dict[str, Any]]) -> None:
        self.rows = iter(rows)

    def next_frame(self, frame_id: int, timestamp: datetime) -> dict[str, Any] | None:
        row = next(self.rows, None)
        if row is None:
            return None
        return user_csv_row_to_frame(row, frame_id=frame_id, timestamp=timestamp)
