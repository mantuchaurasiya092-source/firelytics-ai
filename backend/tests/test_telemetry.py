from __future__ import annotations

import json
import math
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from telemetry.anomaly_detection import TelemetryAnomalyDetector
from telemetry.ingestion import parse_telemetry_csv, psi101_raw_row_to_frame, user_csv_row_to_frame
from telemetry.simulator import SCENARIOS, SyntheticTelemetryGenerator, TELEMETRY_FIELDS
from telemetry.streaming import TelemetryHub, TelemetryModeRequest


client = TestClient(app)


def test_synthetic_generator_has_requested_fields_and_json_safe_comms_gaps():
    generator = SyntheticTelemetryGenerator(
        "communication_interruption",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    nominal = generator.generate(0)
    interruption = generator.generate(4)

    assert set(TELEMETRY_FIELDS).issubset(nominal)
    assert nominal["source_mode"] == "SYNTHETIC"
    assert nominal["scenario"] == "communication_interruption"
    assert all(math.isfinite(nominal[name]) for name in TELEMETRY_FIELDS if name != "sensor_noise_profile")
    assert all(interruption[name] is None for name in TELEMETRY_FIELDS if name != "sensor_noise_profile")
    assert interruption["sensor_noise_profile"] == "synthetic_packet_gap"
    json.dumps([nominal, interruption], allow_nan=False)
    assert len(SCENARIOS) == 7


def test_rule_engine_catches_sudden_temperature_spike_with_structured_alert():
    generator = SyntheticTelemetryGenerator(
        "sudden_temperature_spike",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    detector = TelemetryAnomalyDetector()
    previous = None
    alerts = []
    for frame_index in range(7):
        frame = generator.generate(frame_index)
        alerts.extend(detector.evaluate(frame, previous))
        previous = frame

    temperature_alert = next(
        alert for alert in alerts
        if alert["trigger_variables"] == ["temp_c"]
        and alert["what_changed"].startswith("Rule-based:")
    )
    assert temperature_alert["severity"] == "CRITICAL"
    assert temperature_alert["source_mode"] == "SYNTHETIC"
    assert temperature_alert["supporting_observations"]
    assert set(temperature_alert) == {
        "alert_id",
        "timestamp",
        "what_changed",
        "trigger_variables",
        "severity",
        "supporting_observations",
        "source_mode",
    }


def test_anomaly_rules_cover_oxygen_and_airflow_and_statistical_z_score():
    detector = TelemetryAnomalyDetector()
    previous = {
        "timestamp": "t0",
        "source_mode": "SYNTHETIC",
        "source_elapsed_s": 0.0,
        "O2_pct": 21.0,
        "airflow_cms": 10.0,
        "temp_c": 20.0,
    }
    current = {
        **previous,
        "timestamp": "t1",
        "source_elapsed_s": 1.0,
        "O2_pct": 18.0,
        "airflow_cms": 0.0,
    }
    rule_alerts = detector.evaluate(current, previous)
    assert {item["trigger_variables"][0] for item in rule_alerts} == {"O2_pct", "airflow_cms"}

    statistical = TelemetryAnomalyDetector()
    for index in range(10):
        stable = {
            "timestamp": f"t{index}",
            "source_mode": "SYNTHETIC",
            "temp_c": 20.0 + index * 0.1,
        }
        statistical.evaluate(stable)
    outlier = {"timestamp": "outlier", "source_mode": "SYNTHETIC", "temp_c": 40.0}
    outlier_alerts = statistical.evaluate(outlier)
    assert any(item["what_changed"].startswith("Rolling z-score:") for item in outlier_alerts)


def test_psi101_replay_does_not_mislabel_instrument_channels_as_cabin_values():
    frame = psi101_raw_row_to_frame(
        {
            "TimeString": "2010/235/09:14:17",
            "ElapsedTestTime(Secs)": "201",
            "GasPlumeTemperature(DegC)": "29.6907",
            "DustTrakAMeasurement(MgPerM3)": "20013",
            "SampleSidePressure[AT20](PSIA)": "14.9429",
            "MFCMassFlowRate(LPM)": "0",
        },
        frame_id=1,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert frame["source_mode"] == "REPLAY"
    assert frame["temp_c"] == 29.6907
    assert frame["O2_pct"] is None
    assert frame["pressure_psi"] is None
    assert frame["airflow_cms"] is None
    assert frame["smoke_mg_m3"] is None
    assert frame["source_measurements"]["aerosol_mass_mg_m3"] == 20013.0
    assert frame["source_measurements"]["mfc_mass_flow_lpm"] == 0.0


def test_csv_parser_keeps_missing_values_null_and_rejects_bad_numbers():
    rows, headers = parse_telemetry_csv(
        "timestamp,temp_c,O2_pct,airflow_cms\n2026-01-01T00:00:00Z,20,,10\n"
    )
    assert headers[0] == "timestamp"
    assert rows[0]["temp_c"] == 20.0
    assert rows[0]["O2_pct"] is None
    assert rows[0]["airflow_cms"] == 10.0

    try:
        parse_telemetry_csv("temp_c\nnot-a-number\n")
    except ValueError as exc:
        assert "not numeric" in str(exc)
    else:
        raise AssertionError("Invalid measurement text must not be silently accepted.")

    raw_rows, _ = parse_telemetry_csv(
        "GasPlumeTemperature(DegC),DustTrakAMeasurement(MgPerM3),"
        "MFCMassFlowRate(LPM),SampleSidePressure[AT20](PSIA)\n"
        "29.7,20013,1.2,14.9\n"
    )
    raw_frame = user_csv_row_to_frame(
        raw_rows[0],
        frame_id=1,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert raw_frame["temp_c"] == 29.7
    assert raw_frame["smoke_mg_m3"] is None
    assert raw_frame["airflow_cms"] is None
    assert raw_frame["source_measurements"]["aerosol_mass_mg_m3"] == 20013.0
    assert raw_frame["source_measurements"]["mfc_mass_flow_lpm"] == 1.2


def test_polling_routes_support_synthetic_mode_and_csv_upload():
    mode_response = client.post(
        "/api/telemetry/mode",
        json={"mode": "synthetic", "scenario": "sudden_temperature_spike"},
    )
    assert mode_response.status_code == 200
    assert mode_response.json()["data_label"].startswith("SYNTHETIC")

    snapshots = [
        client.get("/telemetry/stream").json()
        for _ in range(7)
    ]
    assert snapshots[-1]["latest_frame"]["source_mode"] == "SYNTHETIC"
    assert snapshots[-1]["history"][-1]["frame_id"] == 7
    assert any(
        alert["trigger_variables"] == ["temp_c"]
        for alert in snapshots[-1]["active_anomalies"]
    )

    missing_upload = client.post(
        "/telemetry/mode",
        json={"mode": "upload"},
    )
    assert missing_upload.status_code == 409

    uploaded = client.post(
        "/api/telemetry/upload",
        content="timestamp,temp_c,airflow_cms\n2026-01-01T00:00:00Z,24.5,8\n",
        headers={"content-type": "text/csv"},
    )
    assert uploaded.status_code == 200
    frame = client.get("/api/telemetry/stream").json()["latest_frame"]
    assert frame["source_mode"] == "REPLAY"
    assert frame["temp_c"] == 24.5
    assert frame["airflow_cms"] == 8.0
    assert "NOT INDEPENDENTLY VERIFIED" in client.get("/api/telemetry/stream").json()["data_label"]


def test_stream_history_is_bounded_to_the_latest_sixty_frames():
    hub = TelemetryHub()
    hub.configure(TelemetryModeRequest(mode="synthetic"))
    snapshot = None
    for _ in range(65):
        snapshot = hub.snapshot()

    assert snapshot is not None
    assert len(snapshot["history"]) == 60
    assert snapshot["history"][0]["frame_id"] == 6
    assert snapshot["history"][-1]["frame_id"] == 65


def test_local_psi101_replay_is_labeled_and_preserves_unrecorded_channels():
    mode_response = client.post(
        "/telemetry/mode",
        json={"mode": "replay", "run_id": "63"},
    )
    assert mode_response.status_code == 200
    snapshot = client.get("/api/telemetry/stream").json()
    frame = snapshot["latest_frame"]

    assert snapshot["data_label"].startswith("HISTORICAL REPLAY")
    assert frame["source_mode"] == "REPLAY"
    assert frame["temp_c"] is not None
    assert frame["O2_pct"] is None
    assert frame["pressure_psi"] is None
    assert frame["airflow_cms"] is None
    assert frame["smoke_mg_m3"] is None
    assert frame["source_measurements"]["aerosol_mass_mg_m3"] is not None
