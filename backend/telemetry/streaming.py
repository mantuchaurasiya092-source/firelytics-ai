from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from telemetry.anomaly_detection import TelemetryAnomalyDetector
from telemetry.ingestion import (
    MAX_UPLOAD_BYTES,
    Psi101RawReplayer,
    UserCsvReplayer,
    parse_telemetry_csv,
)
from telemetry.simulator import ScenarioName, SyntheticTelemetryGenerator


TelemetryMode = Literal["synthetic", "replay", "upload"]
router = APIRouter(tags=["virtual spacecraft telemetry"])

UNITS = {
    "O2_pct": "%",
    "PO2_psi": "psi",
    "pressure_psi": "psi",
    "temp_c": "°C",
    "airflow_cms": "cm/s",
    "smoke_mg_m3": "mg/m³",
    "gravity_g": "g",
}
SCIENTIFIC_DISCLAIMER = (
    "Exploratory software-only monitoring. Synthetic values are not NASA telemetry; "
    "replayed values retain source limitations. Rule triggers are not flight alarms, "
    "safety determinations, physical control commands, or validated anomaly probabilities."
)
NOT_RECORDED_BY_PSI101 = [
    "O2_pct",
    "PO2_psi",
    "cabin pressure_psi",
    "airflow_cms",
    "smoke_mg_m3",
    "gravity_g",
]


class TelemetryModeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: TelemetryMode
    scenario: ScenarioName = "nominal_operations"
    run_id: str = Field(default="63", pattern=r"^\d{1,3}$")


class TelemetryHub:
    def __init__(self) -> None:
        self._lock = RLock()
        self._mode: TelemetryMode | None = None
        self._scenario: ScenarioName | None = None
        self._run_id: str | None = None
        self._generator: SyntheticTelemetryGenerator | None = None
        self._replayer: Psi101RawReplayer | UserCsvReplayer | None = None
        self._upload_headers: list[str] = []
        self._upload_rows: list[dict[str, Any]] = []
        self._upload_recorded_fields: list[str] = []
        self._frame_sequence = 0
        self._start_time = datetime.now(timezone.utc)
        self._history: deque[dict[str, Any]] = deque(maxlen=60)
        self._alerts: deque[dict[str, Any]] = deque(maxlen=600)
        self._detector = TelemetryAnomalyDetector()
        self._status = "stopped"

    def _reset(self) -> None:
        self._frame_sequence = 0
        self._start_time = datetime.now(timezone.utc)
        self._history.clear()
        self._alerts.clear()
        self._detector.reset()
        self._status = "running"

    def configure(self, request: TelemetryModeRequest) -> dict[str, Any]:
        with self._lock:
            if request.mode == "upload":
                if not self._upload_rows:
                    raise HTTPException(
                        status_code=409,
                        detail="Upload a CSV before selecting upload mode.",
                    )
                self._mode = "upload"
                self._scenario = None
                self._run_id = None
                self._generator = None
                self._replayer = UserCsvReplayer(self._upload_rows)
                self._reset()
                return self.snapshot(advance=False)

            generator: SyntheticTelemetryGenerator | None = None
            replayer: Psi101RawReplayer | UserCsvReplayer | None = None
            if request.mode == "synthetic":
                generator = SyntheticTelemetryGenerator(request.scenario)
            elif request.mode == "replay":
                try:
                    replayer = Psi101RawReplayer(request.run_id)
                except FileNotFoundError as exc:
                    raise HTTPException(status_code=503, detail=str(exc)) from exc
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=str(exc)) from exc

            self._mode = request.mode
            self._scenario = request.scenario if request.mode == "synthetic" else None
            self._run_id = request.run_id if request.mode == "replay" else None
            self._generator = generator
            self._replayer = replayer
            self._reset()
            return self.snapshot(advance=False)

    def configure_upload(self, content: str) -> dict[str, Any]:
        try:
            rows, headers = parse_telemetry_csv(content)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        with self._lock:
            self._mode = "upload"
            self._scenario = None
            self._run_id = None
            self._generator = None
            self._replayer = UserCsvReplayer(rows)
            self._upload_headers = headers
            self._upload_rows = rows
            self._upload_recorded_fields = sorted({
                field
                for row in rows
                for field in row.get("source_fields_available", [])
            })
            self._reset()
            return self.snapshot(advance=False)

    def _data_label(self) -> str:
        if self._mode == "synthetic":
            return f"SYNTHETIC · {self._scenario or 'nominal_operations'}"
        if self._mode == "replay":
            return (
                f"HISTORICAL REPLAY · PSI-101 SAME-R RUN {self._run_id} · "
                "measured source channels only"
            )
        if self._mode == "upload":
            return "CSV REPLAY · USER-PROVIDED FILE · VALUES NOT INDEPENDENTLY VERIFIED"
        return "NO DATA SOURCE SELECTED"

    def _source_metadata(self) -> dict[str, Any]:
        if self._mode == "synthetic":
            return {
                "source": "deterministic illustrative generator",
                "recorded_fields": list(UNITS),
                "unavailable_fields": [],
                "interpretation": "Every reading is generated and labeled SYNTHETIC.",
            }
        if self._mode == "replay":
            return {
                "source": "locally present PSI-101 SAME-R raw run CSV",
                "run_id": self._run_id,
                "recorded_fields": [
                    "temp_c",
                    "aerosol_mass_mg_m3",
                    "ptrak_particles_cm3",
                    "sample_resistance_ohm",
                    "sample_side_pressure_psia",
                    "mfc_pressure_psia",
                    "mfc_mass_flow_lpm",
                    "lfe_flow_rate_sccm",
                ],
                "unavailable_fields": NOT_RECORDED_BY_PSI101,
                "interpretation": (
                    "Instrument pressure and flow channels are preserved separately; they are not "
                    "cabin pressure, oxygen, or air velocity. DustTrak aerosol mass is not identified as smoke."
                ),
            }
        if self._mode == "upload":
            recorded = set(self._upload_recorded_fields)
            return {
                "source": "user-provided CSV",
                "source_columns": self._upload_headers,
                "recorded_fields": self._upload_recorded_fields,
                "unavailable_fields": [field for field in UNITS if field not in recorded],
                "interpretation": (
                    "CSV values are replayed as supplied and are not independently verified as real or NASA data."
                ),
            }
        return {"source": None, "recorded_fields": [], "unavailable_fields": list(UNITS)}

    def _next_frame(self) -> dict[str, Any] | None:
        if self._mode == "synthetic" and self._generator is not None:
            return self._generator.generate(self._frame_sequence)
        if self._replayer is not None:
            replay_time = self._start_time + timedelta(seconds=self._frame_sequence)
            return self._replayer.next_frame(self._frame_sequence + 1, replay_time)
        return None

    def snapshot(self, *, advance: bool = True) -> dict[str, Any]:
        with self._lock:
            if advance and self._status == "running":
                frame = self._next_frame()
                if frame is None:
                    self._status = "complete"
                else:
                    self._frame_sequence += 1
                    previous = self._history[-1] if self._history else None
                    frame["source_mode"] = (
                        "SYNTHETIC" if self._mode == "synthetic" else "REPLAY"
                    )
                    self._history.append(frame)
                    self._alerts.extend(
                        {
                            "frame_id": frame["frame_id"],
                            "alert": alert,
                        }
                        for alert in self._detector.evaluate(frame, previous)
                    )
            oldest_frame_id = self._history[0]["frame_id"] if self._history else None
            active_alerts = [
                item["alert"] for item in self._alerts
                if oldest_frame_id is not None and item["frame_id"] >= oldest_frame_id
            ]
            return {
                "mode": self._mode,
                "scenario": self._scenario,
                "run_id": self._run_id,
                "status": self._status,
                "data_label": self._data_label(),
                "sampling_interval_seconds": 1,
                "latest_frame": self._history[-1] if self._history else None,
                "history": list(self._history),
                "active_anomalies": active_alerts,
                "source_metadata": self._source_metadata(),
                "units": UNITS,
                "safety_disclaimer": SCIENTIFIC_DISCLAIMER,
            }


hub = TelemetryHub()


@router.post("/telemetry/mode")
@router.post("/api/telemetry/mode")
def set_telemetry_mode(request: TelemetryModeRequest) -> dict[str, Any]:
    return hub.configure(request)


@router.get("/telemetry/stream")
@router.get("/api/telemetry/stream")
def telemetry_stream() -> dict[str, Any]:
    return hub.snapshot()


@router.post("/telemetry/upload")
@router.post("/api/telemetry/upload")
async def upload_telemetry_csv(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in {"text/csv", "text/plain", "application/octet-stream"}:
        raise HTTPException(
            status_code=415,
            detail="Send the CSV file contents with Content-Type: text/csv.",
        )
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"CSV upload exceeds the {MAX_UPLOAD_BYTES}-byte limit.",
            )
        chunks.append(chunk)
    try:
        content = b"".join(chunks).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV upload must be UTF-8 encoded.") from exc
    return hub.configure_upload(content)

