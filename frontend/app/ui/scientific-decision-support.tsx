"use client";

import { useState } from "react";
import { ChartTheme } from "./charts";
import {
  DigitalTwinResponse,
  ExecutiveResearchBrief,
  Scenario,
} from "./model";

type ApiError = { detail?: string | { msg?: string }[] };

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}.`);
  return await response.json() as T;
}

function readTwinSnapshot(): DigitalTwinResponse | null {
  const stored = window.sessionStorage.getItem("firelytics.digitalTwin.latest");
  if (!stored) return null;
  const parsed = JSON.parse(stored) as Partial<DigitalTwinResponse>;
  if (!Array.isArray(parsed.baseline_trajectory) || !Array.isArray(parsed.intervention_trajectory)) {
    throw new Error("The saved digital-twin snapshot has an unexpected shape; rerun the twin simulation.");
  }
  return parsed as DigitalTwinResponse;
}

function escapeMarkdown(value: unknown): string {
  return String(value ?? "—").replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
}

function briefMarkdown(brief: ExecutiveResearchBrief, scenario: Scenario): string {
  const lines = [
    "# FIRELYTICS Scientific Research Brief",
    "",
    `> ${brief.safety_disclaimer}`,
    "",
    "## Active scenario",
    `- Mission: ${escapeMarkdown(scenario.mission)}`,
    `- O₂: ${scenario.oxygen_pct}%`,
    `- Pressure: ${scenario.pressure_psi} psi`,
    `- Gravity: ${scenario.gravity_g} g`,
    `- Airflow: ${scenario.airflow_cms} cm/s`,
    `- Material: ${escapeMarkdown(scenario.material)}`,
    "",
    "## Catalogue relevance",
    ...brief.relevance_ranking.map((item) => `- [${item.psi_id} · ${escapeMarkdown(item.name)}](${item.source_url}) — catalogue similarity ${item.match_score}; ${escapeMarkdown(item.local_data_status?.replace(/local/gi, "project"))}`),
    "",
    "## Telemetry anomalies",
    `- Status: ${brief.anomaly_analysis.status}; source: ${escapeMarkdown(brief.anomaly_analysis.source_mode)}`,
    ...brief.anomaly_analysis.alerts.map((alert) => `- ${alert.severity}: ${escapeMarkdown(alert.what_changed)} [${alert.trigger_variables.join(", ")}]`),
    "",
    "## ML insights",
    `- ${brief.ml_insights.provenance}`,
    ...(brief.ml_insights.prediction ? [`- Caller-provided prediction: ${escapeMarkdown(JSON.stringify(brief.ml_insights.prediction))}`] : ["- No prediction supplied."]),
    "",
    "## Intervention comparison",
    `- ${brief.intervention_comparison.interpretation}`,
    "",
    "## Evidence gaps",
    ...brief.evidence_gaps.map((gap) => `- ${gap.psi_id ? `${gap.psi_id}: ` : ""}${escapeMarkdown(gap.gap)}${gap.source_url ? ` (${gap.source_url})` : ""}`),
    "",
    "## RAG supporting citations",
    ...brief.supporting_citations.map((citation) => `- ${citation.psi_id ?? "Project source"} · ${escapeMarkdown(citation.title)} — ${escapeMarkdown(citation.source_path_or_url)}: “${escapeMarkdown(citation.excerpt)}”`),
    "",
    "## Epistemic separation",
    `- Measured data: ${escapeMarkdown(brief.epistemic_separation.measured_data.status)}`,
    `- Calculated surrogates: ${escapeMarkdown(brief.epistemic_separation.calculated_surrogates.interpretation)}`,
    `- Generated LLM suggestions: ${brief.epistemic_separation.generated_llm_suggestions.status}; none generated.`,
    "",
  ];
  return lines.join("\n");
}

export function ScientificDecisionSupport({
  scenario,
  theme,
}: {
  scenario: Scenario;
  theme: ChartTheme;
}) {
  const [brief, setBrief] = useState<ExecutiveResearchBrief | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function synthesize() {
    setLoading(true);
    setError("");
    const warnings: string[] = [];
    const [telemetryResult, mlResult] = await Promise.allSettled([
      getJson<Record<string, unknown>>("telemetry/stream"),
      getJson<Record<string, unknown>>("ml/models"),
    ]);
    const telemetry = telemetryResult.status === "fulfilled" ? telemetryResult.value : null;
    const ml = mlResult.status === "fulfilled" ? mlResult.value : null;
    if (telemetryResult.status === "rejected") warnings.push(`Telemetry unavailable: ${telemetryResult.reason instanceof Error ? telemetryResult.reason.message : "request failed"}`);
    if (mlResult.status === "rejected") warnings.push(`ML registry unavailable: ${mlResult.reason instanceof Error ? mlResult.reason.message : "request failed"}`);

    let twin: DigitalTwinResponse | null = null;
    try {
      twin = readTwinSnapshot();
    } catch (snapshotError) {
      warnings.push(snapshotError instanceof Error ? snapshotError.message : "Digital-twin snapshot could not be read.");
    }

    try {
      const response = await fetch("/api/backend/decision-support/synthesize", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          scenario,
          telemetry_state: telemetry,
          digital_twin_state: twin,
          ml_state: ml,
          integration_warnings: warnings,
        }),
        cache: "no-store",
      });
      if (!response.ok) {
        const info = await response.json().catch(() => ({})) as ApiError;
        const detail = Array.isArray(info.detail)
          ? info.detail.map((item) => item.msg ?? "Invalid input").join("; ")
          : info.detail;
        throw new Error(typeof detail === "string" ? detail : `Synthesis request failed (${response.status}).`);
      }
      setBrief(await response.json() as ExecutiveResearchBrief);
    } catch (requestError) {
      setBrief(null);
      setError(requestError instanceof Error ? requestError.message : "The research brief could not be generated.");
    } finally {
      setLoading(false);
    }
  }

  function downloadMarkdown() {
    if (!brief) return;
    const blob = new Blob([briefMarkdown(brief, scenario)], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "firelytics-scientific-research-brief.md";
    link.click();
    URL.revokeObjectURL(url);
  }

  const physics = brief?.epistemic_separation.calculated_surrogates.physics;
  const isDark = theme === "dark";
  return (
    <div className="shell decision-support-workspace">
      <section className="panel decision-support-heading">
        <div className="panel-head">
          <div>
            <p className="eyebrow">PHASE 6 · EVIDENCE-LINKED PLATFORM SYNTHESIS</p>
            <h1>Scientific Decision Support</h1>
          </div>
          <span className="pill">NO AUTOMATED SAFETY DECISIONS</span>
        </div>
        <p>
          Deterministic aggregation of the active scenario, NASA PSI catalogue context, retrieved RAG citations,
          and explicitly supplied subsystem snapshots. This workspace does not issue operational recommendations.
        </p>
        <div className="decision-support-action-row">
          <button className="button primary decision-support-synthesize" type="button" onClick={() => void synthesize()} disabled={loading}>
            {loading ? "Synthesizing platform data…" : "Synthesize Platform Data"}
          </button>
          {brief && <button className="button ghost" type="button" onClick={downloadMarkdown}>Download Markdown</button>}
        </div>
      </section>

      <section className="panel decision-scenario-context">
        <p className="eyebrow">ACTIVE SCENARIO CONTEXT · USER INPUTS</p>
        <div className="decision-kpi-grid">
          <div><span>O₂</span><strong>{scenario.oxygen_pct}%</strong></div>
          <div><span>Pressure</span><strong>{scenario.pressure_psi} psi</strong></div>
          <div><span>Gravity</span><strong>{scenario.gravity_g} g</strong></div>
          <div><span>Flow</span><strong>{scenario.airflow_cms} cm/s</strong></div>
        </div>
        <p className="small-caution">Mission: {scenario.mission} · Material: {scenario.material || "not specified"} · Scenario inputs are not sensor measurements.</p>
      </section>

      {error && <div className="panel decision-support-error" role="alert">{error}</div>}
      {brief && (
        <>
          <section className="decision-support-grid" aria-label="Executive research brief sections">
            <article className="panel decision-support-card">
              <p className="eyebrow">01 · CATALOGUE &amp; PHYSICS</p>
              <h2>Relevant NASA investigations</h2>
              <ul className="decision-list">
                {brief.relevance_ranking.map((item) => (
                  <li key={item.psi_id}>
                    <a href={item.source_url} target="_blank" rel="noreferrer">{item.psi_id} · {item.name} ↗</a>
                    <span>Catalogue match {item.match_score} · coverage {item.evidence_coverage}</span>
                    <small>{item.local_data_status?.replace(/local/gi, "project") ?? "Evidence status not reported"}</small>
                  </li>
                ))}
              </ul>
              {physics?.status === "computed" ? (
                <p className="decision-surrogate"><b>MOC screening surrogate:</b> {physics.estimated_moc_pct}% · regime {physics.regime_classification}. Not validated, measured, or an operational limit.</p>
              ) : (
                <p className="decision-surrogate">{physics?.interpretation ?? "Physics surrogate not computed; required scenario inputs are missing."}</p>
              )}
            </article>

            <article className="panel decision-support-card">
              <p className="eyebrow">02 · TELEMETRY &amp; ML</p>
              <h2>Alerts and model evidence</h2>
              <p><b>Telemetry:</b> {brief.anomaly_analysis.status} · {brief.anomaly_analysis.alert_count} alert(s) · source {brief.anomaly_analysis.source_mode ?? "not reported"}</p>
              {brief.anomaly_analysis.alerts.length ? (
                <ul className="decision-list">
                  {brief.anomaly_analysis.alerts.slice(0, 8).map((alert) => (
                    <li key={alert.alert_id}><span>{alert.severity} · {alert.what_changed}</span><small>Triggers: {alert.trigger_variables.join(", ")}</small></li>
                  ))}
                </ul>
              ) : <p>No active alerts were supplied; this is not evidence that the scenario is safe.</p>}
              <p><b>ML:</b> {brief.ml_insights.prediction ? JSON.stringify(brief.ml_insights.prediction) : "No live prediction supplied."}</p>
              {brief.ml_insights.models.length > 0 && (
                <ul className="decision-list">
                  {brief.ml_insights.models.map((model) => (
                    <li key={model.model_id}>
                      <span>{model.display_name} · historical grouped validation</span>
                      <small>
                        Accuracy {model.validation_metrics.accuracy.toFixed(3)} · F1 {model.validation_metrics.f1.toFixed(3)}
                        {model.validation_metrics.roc_auc === null ? " · ROC-AUC unavailable" : ` · ROC-AUC ${model.validation_metrics.roc_auc.toFixed(3)}`}
                      </small>
                    </li>
                  ))}
                </ul>
              )}
              <p className="small-caution">Registry metrics, if available, are historical grouped validation results—not a current prediction. {brief.ml_insights.provenance}</p>
            </article>

            <article className="panel decision-support-card">
              <p className="eyebrow">03 · DIGITAL TWIN</p>
              <h2>Intervention comparison</h2>
              <p>{brief.intervention_comparison.interpretation}</p>
              {brief.intervention_comparison.status === "caller_provided" && (
                <div className="decision-trajectory-summary">
                  <span>Baseline points <b>{brief.intervention_comparison.baseline_trajectory.length}</b></span>
                  <span>Intervention points <b>{brief.intervention_comparison.intervention_trajectory.length}</b></span>
                </div>
              )}
              {brief.intervention_comparison.assumptions_and_uncertainty?.slice(0, 3).map((item) => <small key={item}>{item}</small>)}
              {brief.intervention_comparison.safety_disclaimer && <p className="small-caution">{brief.intervention_comparison.safety_disclaimer}</p>}
            </article>

            <article className="panel decision-support-card">
              <p className="eyebrow">04 · AI RAG &amp; EVIDENCE GAPS</p>
              <h2>Retrieved evidence, not generated authority</h2>
              {brief.evidence_gaps.map((item, index) => (
                <p key={`${item.psi_id ?? "gap"}-${index}`}>
                  <b>{item.psi_id ?? "Evidence gap"}:</b> {item.gap}{" "}
                  {item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Source ↗</a>}
                </p>
              ))}
              <ul className="decision-list">
                {brief.supporting_citations.map((citation) => (
                  <li key={citation.chunk_id}>
                    <a href={citation.source_path_or_url} target="_blank" rel="noreferrer">{citation.psi_id ?? "Project source"} · {citation.title} ↗</a>
                    <small>{citation.excerpt}</small>
                  </li>
                ))}
              </ul>
              {!brief.supporting_citations.length && <p>No matching RAG citations were retrieved for this scenario.</p>}
            </article>
          </section>

          <section className="panel decision-epistemic-panel">
            <div className="panel-head"><div><p className="eyebrow">EPISTEMIC SEPARATION</p><h2>What this brief does—and does not—establish</h2></div></div>
            <div className="decision-epistemic-grid">
              <p><span className="decision-dot cyan" /> <b>Measured / supplied data:</b> {String(brief.epistemic_separation.measured_data.status ?? "No independently verified measurements.")}</p>
              <p><span className="decision-dot amber" /> <b>Calculated surrogates:</b> {String(brief.epistemic_separation.calculated_surrogates.interpretation ?? "No surrogate supplied.")}</p>
              <p><span className="decision-dot emerald" /> <b>LLM suggestions:</b> {brief.epistemic_separation.generated_llm_suggestions.status}. No suggestions or safety decision generated.</p>
            </div>
            {brief.integration_warnings.length > 0 && (
              <div className="decision-support-warnings"><b>Unavailable subsystem inputs:</b><ul>{brief.integration_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>
            )}
            <p className="decision-safety">{brief.safety_disclaimer}</p>
          </section>
        </>
      )}
      {!brief && !error && <p className="small-caution">Synthesis retrieves current catalogue/RAG context on request. Telemetry and ML service failures are reported in the generated brief.</p>}
      <span className="sr-only" aria-live="polite">{isDark ? "Dark theme active" : "Light theme active"}</span>
    </div>
  );
}
