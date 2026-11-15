"use client";

import { ChangeEvent, useEffect, useState } from "react";
import {
  TelemetryAlert,
  TelemetryMode,
  TelemetryScenario,
  TelemetrySnapshot,
} from "./model";
import { ChartTheme, LiveTelemetryChart } from "./charts";

const SCENARIOS: { value: TelemetryScenario; label: string }[] = [
  { value: "nominal_operations", label: "Normal operations" },
  { value: "gradual_overheat", label: "Gradual overheat" },
  { value: "sudden_temperature_spike", label: "Sudden temperature spike" },
  { value: "abnormal_oxygen", label: "Abnormal oxygen depletion" },
  { value: "airflow_failure", label: "Airflow failure" },
  { value: "sensor_noise_spike", label: "Sensor noise spike" },
  { value: "communication_interruption", label: "Communications interruption" },
];

const REPLAY_RUNS = ["63", "64", "76", "84", "95", "97"];

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    let message = `Telemetry request failed (${response.status}).`;
    try {
      const body = await response.json() as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      message = `Telemetry request failed (${response.status}) with a non-JSON response.`;
    }
    throw new Error(message);
  }
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new Error("Telemetry API returned an unexpected response format.");
  }
  return await response.json() as T;
}

function alertClass(alert: TelemetryAlert): string {
  return alert.severity === "CRITICAL"
    ? "telemetry-alert telemetry-alert-critical"
    : "telemetry-alert telemetry-alert-caution";
}

export function VirtualSpacecraftMonitoring({ theme }: { theme: ChartTheme }) {
  const [mode, setMode] = useState<TelemetryMode>("synthetic");
  const [scenario, setScenario] = useState<TelemetryScenario>("nominal_operations");
  const [runId, setRunId] = useState("63");
  const [snapshot, setSnapshot] = useState<TelemetrySnapshot | null>(null);
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");
  const [uploadReady, setUploadReady] = useState(false);

  useEffect(() => {
    if (!running) return undefined;
    const controller = new AbortController();
    let active = true;
    let timer: number | undefined;

    const poll = async () => {
      try {
        const result = await requestJson<TelemetrySnapshot>("telemetry/stream", {
          signal: controller.signal,
        });
        if (!active) return;
        setSnapshot(result);
        setError("");
        if (result.status === "complete") {
          setRunning(false);
          return;
        }
      } catch (requestError) {
        if (requestError instanceof Error && requestError.name === "AbortError") return;
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Telemetry polling failed.");
          setRunning(false);
        }
        return;
      }
      if (active) timer = window.setTimeout(poll, 1000);
    };

    void poll();
    return () => {
      active = false;
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [running]);

  async function startMonitoring() {
    if (mode === "upload" && !uploadReady) {
      setError("Select and successfully load a CSV file before starting upload replay.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await requestJson<TelemetrySnapshot>("telemetry/mode", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ mode, scenario, run_id: runId }),
      });
      setSnapshot(result);
      setRunning(true);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to start telemetry.");
    } finally {
      setBusy(false);
    }
  }

  async function uploadCsv(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    setMode("upload");
    setRunning(false);
    setUploadReady(false);
    setBusy(true);
    setError("");
    setFileName(file.name);
    try {
      const csv = await file.text();
      const result = await requestJson<TelemetrySnapshot>("telemetry/upload", {
        method: "POST",
        headers: { "content-type": "text/csv" },
        body: csv,
      });
      setSnapshot(result);
      setUploadReady(true);
      setRunning(true);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to replay the CSV file.");
    } finally {
      setBusy(false);
      input.value = "";
    }
  }

  const alerts = snapshot?.active_anomalies ?? [];
  const latest = snapshot?.latest_frame;
  const sourceLabel = snapshot?.data_label ?? "NO DATA SOURCE SELECTED";
  const sourceKind = latest?.source_mode ?? (mode === "synthetic" ? "SYNTHETIC" : "REPLAY");

  return (
    <div className="telemetry-workspace">
      <header className="telemetry-workspace-heading">
        <div>
          <p className="eyebrow">PHASE 4 · SOFTWARE-ONLY TELEMETRY</p>
          <h1>Virtual Spacecraft Monitoring</h1>
          <p>
            One frame per poll, bounded to a rolling 60-frame history. Anomaly
            messages expose their exact rules; they are not flight alarms or
            operational safety determinations.
          </p>
        </div>
        <span className={`telemetry-source-badge telemetry-source-${sourceKind.toLowerCase()}`}>
          {sourceLabel}
        </span>
      </header>

      <section className="telemetry-safety-note" aria-label="Telemetry provenance and limitations">
        <strong>Provenance guardrail</strong>
        <span>
          Synthetic values are labeled <b>SYNTHETIC</b>. PSI-101 data is labeled
          <b> HISTORICAL REPLAY</b> and only channels actually present in the
          source CSV are mapped. In particular, those files do not provide cabin
          O₂, cabin pressure, cm/s airflow, gravity, or a smoke-specific
          measurement; instrument pressure/flow and aerosol readings are not
          substituted for them. User CSVs are unverified.
        </span>
      </section>

      <section className="panel telemetry-control-panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">TELEMETRY CONTROL PANEL</p>
            <h2>Select a software data source</h2>
          </div>
          <span className="pill">{running ? "POLLING · 1 HZ" : snapshot?.status?.toUpperCase() ?? "STOPPED"}</span>
        </div>
        <div className="telemetry-controls">
          <label className="field">
            <span>Telemetry mode</span>
            <select
              value={mode}
              onChange={(event) => {
                setRunning(false);
                setMode(event.target.value as TelemetryMode);
              }}
            >
              <option value="synthetic">Synthetic Generator</option>
              <option value="replay">Historical PSI-101 Replay</option>
              <option value="upload">CSV Upload</option>
            </select>
          </label>
          {mode === "synthetic" && (
            <label className="field">
              <span>Synthetic scenario</span>
              <select
                value={scenario}
                onChange={(event) => setScenario(event.target.value as TelemetryScenario)}
              >
                {SCENARIOS.map((item) => (
                  <option value={item.value} key={item.value}>{item.label}</option>
                ))}
              </select>
            </label>
          )}
          {mode === "replay" && (
            <label className="field">
              <span>Reconciled PSI-101 run</span>
              <select value={runId} onChange={(event) => setRunId(event.target.value)}>
                {REPLAY_RUNS.map((id) => <option value={id} key={id}>Run {id}</option>)}
              </select>
            </label>
          )}
          {mode === "upload" && (
            <label className="field telemetry-file-field">
              <span>CSV file · max 2 MB</span>
              <input type="file" accept=".csv,text/csv" onChange={uploadCsv} disabled={busy} />
              {fileName && <small>{fileName}</small>}
            </label>
          )}
          <div className="telemetry-control-actions">
            {running ? (
              <button className="button secondary" type="button" onClick={() => setRunning(false)}>
                Stop polling
              </button>
            ) : (
              <button
                className="button primary"
                type="button"
                onClick={startMonitoring}
                disabled={busy || (mode === "upload" && !uploadReady)}
              >
                {busy ? "Configuring…" : "Start monitoring"}
              </button>
            )}
          </div>
        </div>
        {error && <div className="telemetry-error" role="alert">{error}</div>}
        <p className="telemetry-rule-note">
          Rule thresholds: O₂ decrease &gt; 2 percentage points; temperature
          rise &gt; 50 °C/s; airflow transition to ≤ 0.5 cm/s; rolling
          |z-score| &gt; 3 after at least 8 prior samples. These are exploratory
          software triggers, not NASA limits. No confidence score is generated.
        </p>
      </section>

      <section className="panel telemetry-chart-panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">LIVE TIME SERIES · LAST 60 FRAMES</p>
            <h2>Synchronized telemetry tracks</h2>
            <p>Missing or unrecorded channels remain visibly blank; values are never imputed for display.</p>
          </div>
          <span className="pill">{snapshot?.history.length ?? 0} / 60 frames</span>
        </div>
        <LiveTelemetryChart history={snapshot?.history ?? []} theme={theme} />
        {snapshot?.source_metadata.unavailable_fields.length ? (
          <p className="telemetry-missing-note">
            Not recorded by this source: {snapshot.source_metadata.unavailable_fields.join(", ")}.
          </p>
        ) : null}
      </section>

      <section className="panel telemetry-event-panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">EVENT TIMELINE · RULE-BASED AND STATISTICAL</p>
            <h2>Anomaly alert log</h2>
          </div>
          <span className="pill">{alerts.length} recent alerts</span>
        </div>
        <div className="telemetry-event-log" role="log" aria-live="polite">
          {!alerts.length ? (
            <div className="telemetry-alert telemetry-alert-info">
              <strong>INFO</strong>
              <span>
                {snapshot?.history.length
                  ? "No configured rule trigger has been observed in the current window."
                  : "Start a source to receive frames and rule-triggered events."}
              </span>
            </div>
          ) : [...alerts].reverse().map((alert) => (
            <article className={alertClass(alert)} key={alert.alert_id}>
              <div className="telemetry-alert-heading">
                <strong>{alert.severity}</strong>
                <time dateTime={alert.timestamp}>{new Date(alert.timestamp).toLocaleTimeString()}</time>
                <span>MONITOR TRIGGER</span>
                <span>{alert.source_mode}</span>
              </div>
              <p>{alert.what_changed}</p>
              <p><b>Trigger variables:</b> {alert.trigger_variables.join(", ")}</p>
              <ul>
                {alert.supporting_observations.map((observation, index) => (
                  <li key={`${alert.alert_id}-${index}`}>{observation}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
        <p className="telemetry-disclaimer">{snapshot?.safety_disclaimer}</p>
      </section>
    </div>
  );
}
