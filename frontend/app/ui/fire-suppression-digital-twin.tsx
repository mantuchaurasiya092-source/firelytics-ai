"use client";

import { FormEvent, useState } from "react";
import { ChartTheme, DigitalTwinComparisonChart } from "./charts";
import { DigitalTwinResponse } from "./model";

type InterventionKind = "ventilation_cutoff" | "depressurization" | "inert_gas" | "gravity_shift";
type InertSpecies = "CO2" | "Helium";

type ApiError = { detail?: string | { msg?: string }[] };

const REFERENCE_LINKS: Record<string, { url: string; doi: string }> = {
  "PSI-25 BASS-II": {
    url: "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25",
    doi: "10.60555/4qc4-de67",
  },
  "PSI-69 FLEX": {
    url: "https://psi.nasa.gov/physci/repo/data/investigations/PSI-69",
    doi: "10.60555/mbq8-0451",
  },
  "PSI-98 SAFFIRE-I": {
    url: "https://psi.nasa.gov/physci/repo/data/investigations/PSI-98",
    doi: "10.60555/0t15-1z43",
  },
};

function optionalNumber(value: string): number | undefined {
  return value.trim() === "" ? undefined : Number(value);
}

export function FireSuppressionDigitalTwin({ theme }: { theme: ChartTheme }) {
  const [oxygen, setOxygen] = useState("21");
  const [pressure, setPressure] = useState("14.7");
  const [airflow, setAirflow] = useState("10");
  const [gravity, setGravity] = useState("1");
  const [temperature, setTemperature] = useState("");
  const [flameVolume, setFlameVolume] = useState("");
  const [kind, setKind] = useState<InterventionKind>("ventilation_cutoff");
  const [targetOxygen, setTargetOxygen] = useState("");
  const [targetPressure, setTargetPressure] = useState("");
  const [targetGravity, setTargetGravity] = useState("");
  const [inertSpecies, setInertSpecies] = useState<InertSpecies>("CO2");
  const [transitionSeconds, setTransitionSeconds] = useState("30");
  const [durationSeconds, setDurationSeconds] = useState("60");
  const [result, setResult] = useState<DigitalTwinResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [snapshotWarning, setSnapshotWarning] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const baseline: Record<string, number | undefined> = {
        oxygen_pct: Number(oxygen),
        pressure_psi: Number(pressure),
        airflow_cms: Number(airflow),
        gravity_g: Number(gravity),
        temp_k: optionalNumber(temperature),
        flame_volume_m3: optionalNumber(flameVolume),
      };
      const intervention: Record<string, string | number | undefined> = {
        kind,
        transition_seconds: Number(transitionSeconds),
      };
      if (kind === "depressurization" || kind === "inert_gas") {
        intervention.target_o2_pct = Number(targetOxygen);
      }
      if (kind === "depressurization") intervention.target_pressure_psi = Number(targetPressure);
      if (kind === "inert_gas") intervention.inert_species = inertSpecies;
      if (kind === "gravity_shift") intervention.target_gravity_g = Number(targetGravity);

      const response = await fetch("/api/backend/digital-twin/simulate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          baseline,
          intervention,
          duration_seconds: Number(durationSeconds),
        }),
        cache: "no-store",
      });
      if (!response.ok) {
        const info = await response.json().catch(() => ({})) as ApiError;
        const detail = Array.isArray(info.detail)
          ? info.detail.map((item) => item.msg ?? "Invalid input").join("; ")
          : info.detail;
        throw new Error(typeof detail === "string" ? detail : `Simulation request failed (${response.status}).`);
      }
      const simulation = await response.json() as DigitalTwinResponse;
      setResult(simulation);
      try {
        window.sessionStorage.setItem("firelytics.digitalTwin.latest", JSON.stringify(simulation));
        setSnapshotWarning("");
      } catch {
        setSnapshotWarning("This browser could not retain the last twin result for the decision-support workspace.");
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The simulation request failed.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="shell digital-twin-workspace">
      <section className="panel digital-twin-hero">
        <div className="panel-head">
          <div>
            <p className="eyebrow">PHASE 5 · EXPLORATORY BOUNDARY-CONDITION COMPARATOR</p>
            <h1>Fire Suppression Digital Twin</h1>
          </div>
          <span className="pill">NO ACTUATION · NOT VALIDATED</span>
        </div>
        <p>
          Compare user-specified atmosphere and gravity scenarios. This prototype does not predict
          extinction, temperature response, flame shape, or suppressant effectiveness.
        </p>
        <p className="digital-twin-safety">
          EXPLORATORY SIMULATION ONLY. Do not use for operational spacecraft hardware actuation.
        </p>
      </section>

      <form className="panel digital-twin-form" onSubmit={submit}>
        <div className="digital-twin-form-grid">
          <section className="digital-twin-form-section">
            <p className="eyebrow">BASELINE · SCENARIO INPUTS</p>
            <div className="digital-twin-fields">
              <label className="field">
                <span>Initial O₂ · %</span>
                <input type="number" min="0" max="100" step="any" value={oxygen} onChange={(event) => setOxygen(event.target.value)} required />
              </label>
              <label className="field">
                <span>Pressure · psi</span>
                <input type="number" min="0.001" max="30" step="any" value={pressure} onChange={(event) => setPressure(event.target.value)} required />
              </label>
              <label className="field">
                <span>Airflow · cm/s</span>
                <input type="number" min="0" max="250" step="any" value={airflow} onChange={(event) => setAirflow(event.target.value)} required />
              </label>
              <label className="field">
                <span>Gravity · g</span>
                <input type="number" min="0" max="2" step="any" value={gravity} onChange={(event) => setGravity(event.target.value)} required />
              </label>
              <label className="field">
                <span>Temperature · K (optional context)</span>
                <input type="number" min="0.001" max="5000" step="any" value={temperature} onChange={(event) => setTemperature(event.target.value)} />
              </label>
              <label className="field">
                <span>Flame volume · m³ (optional context)</span>
                <input type="number" min="0.000001" step="any" value={flameVolume} onChange={(event) => setFlameVolume(event.target.value)} />
              </label>
            </div>
            <small className="digital-twin-hint">
              Starting values are illustrative form defaults, not a NASA habitat profile. Temperature and volume are only carried through.
            </small>
          </section>

          <section className="digital-twin-form-section">
            <p className="eyebrow">INTERVENTION · ENVIRONMENT BOUNDARIES ONLY</p>
            <div className="digital-twin-fields">
              <label className="field">
                <span>Scenario</span>
                <select value={kind} onChange={(event) => setKind(event.target.value as InterventionKind)}>
                  <option value="ventilation_cutoff">HVAC ventilation cutoff</option>
                  <option value="inert_gas">CO₂ / helium scenario</option>
                  <option value="depressurization">Cabin depressurization / O₂ vitiation</option>
                  <option value="gravity_shift">Gravity boundary shift</option>
                </select>
              </label>
              {kind === "depressurization" && (
                <>
                  <label className="field">
                    <span>User-set target O₂ · %</span>
                    <input type="number" min="0" max="100" step="any" value={targetOxygen} onChange={(event) => setTargetOxygen(event.target.value)} required />
                  </label>
                  <label className="field">
                    <span>User-set target pressure · psi</span>
                    <input type="number" min="0.001" max="30" step="any" value={targetPressure} onChange={(event) => setTargetPressure(event.target.value)} required />
                  </label>
                </>
              )}
              {kind === "inert_gas" && (
                <>
                  <label className="field">
                    <span>Inert species · context only</span>
                    <select value={inertSpecies} onChange={(event) => setInertSpecies(event.target.value as InertSpecies)}>
                      <option value="CO2">CO₂</option>
                      <option value="Helium">Helium</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>User-set target O₂ · %</span>
                    <input type="number" min="0" max="100" step="any" value={targetOxygen} onChange={(event) => setTargetOxygen(event.target.value)} required />
                  </label>
                  <small className="digital-twin-hint">
                    Target is not an MOC or recommendation. No CO₂/helium effectiveness is estimated.
                  </small>
                </>
              )}
              {kind === "gravity_shift" && (
                <label className="field">
                  <span>User-set target gravity · g</span>
                  <input type="number" min="0" max="2" step="any" value={targetGravity} onChange={(event) => setTargetGravity(event.target.value)} required />
                </label>
              )}
              {kind !== "ventilation_cutoff" && (
                <label className="field">
                  <span>Linear transition duration · s</span>
                  <input type="number" min="0.001" max="3600" step="any" value={transitionSeconds} onChange={(event) => setTransitionSeconds(event.target.value)} required />
                </label>
              )}
              <label className="field">
                <span>Comparison duration · s</span>
                <input type="number" min="0.001" max="3600" step="any" value={durationSeconds} onChange={(event) => setDurationSeconds(event.target.value)} required />
              </label>
            </div>
            <button className="button primary digital-twin-submit" type="submit" disabled={loading}>
              {loading ? "Running scenario…" : "Run Digital Twin Simulation"}
            </button>
          </section>
        </div>
      </form>

      {error && <div className="panel"><p className="digital-twin-error" role="alert">{error}</p></div>}
      {snapshotWarning && <p className="small-caution" role="status">{snapshotWarning}</p>}
      {result && (
        <>
          <section className="panel">
            <div className="panel-head">
              <div><p className="eyebrow">COMPARISON · ENVIRONMENT BOUNDARY CONDITION</p><h2>Baseline vs. intervention</h2></div>
              <span className="pill">SCENARIO INTERPOLATION · NOT A FIRE PREDICTION</span>
            </div>
            <DigitalTwinComparisonChart
              baseline={result.baseline_trajectory}
              intervention={result.intervention_trajectory}
              field={kind === "ventilation_cutoff" ? "airflow_cms" : kind === "depressurization" ? "pressure_psi" : kind === "gravity_shift" ? "gravity_g" : "o2_pct"}
              theme={theme}
            />
            <p className="small-caution">
              The selected environmental boundary condition is plotted. Temperature and flame volume are unchanged context, not predicted responses.
            </p>
          </section>
          <section className="panel digital-twin-transparency">
            <div className="panel-head"><div><p className="eyebrow">READ-ONLY SCIENTIFIC TRANSPARENCY</p><h2>Assumptions &amp; uncertainty</h2></div><span className="pill">CALIBRATED: NO</span></div>
            <ul>{result.assumptions_and_uncertainty.map((item) => <li key={item}>{item}</li>)}</ul>
            <h3>Scientific references · contextual only</h3>
            <p className="muted">These PSI records describe relevant research areas; numerical experiment data are not bundled here and were not used to fit this scenario engine.</p>
            <div className="digital-twin-references">
              {result.scientific_references.map((reference) => {
                const link = REFERENCE_LINKS[reference];
                return link ? (
                  <a key={reference} className="pill" href={link.url} target="_blank" rel="noreferrer">
                    {reference} · DOI {link.doi} ↗
                  </a>
                ) : <span className="pill" key={reference}>{reference}</span>;
              })}
            </div>
            <p className="digital-twin-safety">{result.safety_disclaimer}</p>
          </section>
        </>
      )}
    </div>
  );
}
