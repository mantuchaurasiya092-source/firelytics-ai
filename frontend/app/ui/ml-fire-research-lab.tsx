"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  MlModel,
  MlModelRegistry,
  MlPrediction,
  MlShapSummary,
} from "./model";
import {
  ChartTheme,
  MlConfusionRocChart,
  MlShapFeatureChart,
} from "./charts";

const FEATURE_INPUTS = [
  {
    name: "dusttrak_b_mass_mg_m3",
    label: "DustTrak B mass concentration",
    unit: "mg/m³",
  },
  {
    name: "ptrak_particles_cm3",
    label: "P-Trak particle number",
    unit: "particles/cm³",
  },
  {
    name: "gas_plume_temp_c",
    label: "Gas plume temperature",
    unit: "°C",
  },
  {
    name: "sample_resistance_ohms",
    label: "Sample heater resistance",
    unit: "Ω",
  },
  {
    name: "mfc_mass_flow_lpm",
    label: "MFC mass flow rate",
    unit: "L/min",
  },
] as const;

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, {
    ...init,
    cache: "no-store",
    headers: { accept: "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    try {
      const body = await response.json() as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      detail = `Request failed (${response.status}) with a non-JSON response.`;
    }
    throw new Error(detail);
  }
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new Error("The model API returned an unexpected response format.");
  }
  return await response.json() as T;
}

function percentage(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${(value * 100).toFixed(1)}%`
    : "Not available";
}

function metric(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(3)
    : "Not available";
}

export function MlFireResearchLab({ theme }: { theme: ChartTheme }) {
  const [registry, setRegistry] = useState<MlModelRegistry | null>(null);
  const [registryLoading, setRegistryLoading] = useState(true);
  const [registryError, setRegistryError] = useState("");
  const [selectedModelId, setSelectedModelId] = useState("");
  const [explanation, setExplanation] = useState<MlShapSummary[]>([]);
  const [explanationLoading, setExplanationLoading] = useState(false);
  const [explanationError, setExplanationError] = useState("");
  const [featureValues, setFeatureValues] = useState<Record<string, string>>({});
  const [prediction, setPrediction] = useState<MlPrediction | null>(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getJson<MlModelRegistry>("ml/models", { signal: controller.signal })
      .then((result) => {
        setRegistry(result);
        setSelectedModelId((current) => current || result.models[0]?.model_id || "");
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        setRegistryError(error instanceof Error ? error.message : "Unable to load model registry.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setRegistryLoading(false);
      });
    return () => controller.abort();
  }, []);

  const models = registry?.models ?? [];
  const selectedModel: MlModel | undefined = useMemo(
    () => models.find((model) => model.model_id === selectedModelId),
    [models, selectedModelId],
  );
  const featureUnits = Object.fromEntries(
    FEATURE_INPUTS.map(({ name, unit }) => [name, unit]),
  );

  useEffect(() => {
    if (!selectedModelId) {
      setExplanation([]);
      return;
    }
    const controller = new AbortController();
    setExplanationLoading(true);
    setExplanationError("");
    getJson<{ shap_summary: MlShapSummary[] }>(
      `ml/explainability/${encodeURIComponent(selectedModelId)}`,
      { signal: controller.signal },
    )
      .then((result) => setExplanation(result.shap_summary))
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        setExplanationError(error instanceof Error ? error.message : "Unable to load explanations.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setExplanationLoading(false);
      });
    return () => controller.abort();
  }, [selectedModelId]);

  async function submitPrediction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedModel) return;
    const features = Object.fromEntries(
      FEATURE_INPUTS.map(({ name }) => {
        const raw = featureValues[name]?.trim() ?? "";
        return [name, raw === "" ? null : Number(raw)];
      }),
    );
    if (!Object.values(features).some((value) => value !== null)) {
      setPredictionError("Enter at least one measured sensor value before running inference.");
      setPrediction(null);
      return;
    }
    if (Object.values(features).some((value) => value !== null && !Number.isFinite(value))) {
      setPredictionError("Sensor inputs must be finite numeric values in the displayed units.");
      setPrediction(null);
      return;
    }

    setPredictionLoading(true);
    setPredictionError("");
    setPrediction(null);
    try {
      const result = await getJson<MlPrediction>("ml/predict", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          model_id: selectedModelId,
          features,
          feature_units: featureUnits,
        }),
      });
      setPrediction(result);
    } catch (error) {
      setPredictionError(error instanceof Error ? error.message : "Inference failed.");
    } finally {
      setPredictionLoading(false);
    }
  }

  return (
    <div className="ml-workspace">
      <header className="ml-workspace-heading">
        <div>
          <p className="eyebrow">PHASE 3 · GROUPED MODEL EVALUATION</p>
          <h1>ML Fire Research Lab</h1>
          <p>
            Exploratory classifiers for the archived PSI-101
            DustTrak-A observed-band label. Model outputs are separate from
            validated measurements and physical calculations.
          </p>
        </div>
        {registry?.runid_leakage_check_passed && (
          <span className="ml-training-badge">
            GROUP-KFOLD / LEAVE-ONE-RUN-OUT EVALUATION
            <br />
            ZERO RUNID LEAKAGE
          </span>
        )}
      </header>

      <section className="ml-safety-note" aria-label="Scientific scope and limitations">
        <strong>Target limitation</strong>
        <span>
          The target is a binned DustTrak-A aerosol measurement, not a labeled
          fire, ignition, extinction, smoke-versus-dust, or nuisance-dust
          outcome. All 14 mixed-band cycles are excluded. The 5 sensor inputs
          exclude DustTrak-A mass and analog signals used to construct the
          target.
        </span>
      </section>

      {registryLoading && <div className="ml-state" role="status">Loading model registry…</div>}
      {registryError && (
        <div className="ml-state ml-state-error" role="alert">
          <strong>Model registry unavailable</strong>
          <span>{registryError}</span>
          <small>
            Authorized local training uses `python -m pip install -e ".[ml]"` and
            `python -m ml.training.trainer` from `backend/`. It requires the local
            PSI-101 inputs; training is not run by the API. Generated model files
            remain git-ignored pending file-rights review, so deployment requires
            an approved artifact delivery path.
          </small>
        </div>
      )}

      {registry && (
        <>
          <section className="panel ml-registry-panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">MODEL REGISTRY · PSI-101 SAME-R</p>
                <h2>Run-held-out performance</h2>
                <p>{registry.target_interpretation}</p>
              </div>
              <div className="panel-actions">
                <span className="pill">{registry.record_count.toLocaleString()} labeled cycles</span>
                <span className="pill">{registry.run_ids.length} held-out RunIDs</span>
              </div>
            </div>
            <div className="ml-model-grid">
              {models.map((model) => (
                <button
                  type="button"
                  key={model.model_id}
                  className={`ml-model-card ${selectedModelId === model.model_id ? "selected" : ""}`}
                  onClick={() => {
                    setSelectedModelId(model.model_id);
                    setPrediction(null);
                    setPredictionError("");
                  }}
                  aria-pressed={selectedModelId === model.model_id}
                >
                  <span className="ml-model-card-title">{model.display_name}</span>
                  <span className="ml-model-version">v{model.version} · project artifact</span>
                  <span className="ml-model-metrics">
                    <span>Accuracy <b>{percentage(model.validation_metrics.accuracy)}</b></span>
                    <span>Precision <b>{percentage(model.validation_metrics.precision)}</b></span>
                    <span>Recall <b>{percentage(model.validation_metrics.recall)}</b></span>
                    <span>F1 <b>{percentage(model.validation_metrics.f1)}</b></span>
                    <span>ROC-AUC <b>{metric(model.validation_metrics.roc_auc)}</b></span>
                  </span>
                  <span className="ml-model-source">PSI-101 · grouped out-of-fold evaluation</span>
                </button>
              ))}
            </div>
            {selectedModel && (
              <>
                <div className="ml-registry-table-wrap">
                  <table className="ml-registry-table">
                    <thead>
                      <tr>
                        <th>Algorithm</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F1</th>
                        <th>ROC-AUC</th>
                        <th>Majority baseline accuracy</th>
                        <th>Δ accuracy</th>
                      </tr>
                    </thead>
                    <tbody>
                      {models.map((model) => (
                        <tr key={model.model_id}>
                          <th scope="row">{model.display_name}</th>
                          <td>{percentage(model.validation_metrics.precision)}</td>
                          <td>{percentage(model.validation_metrics.recall)}</td>
                          <td>{percentage(model.validation_metrics.f1)}</td>
                          <td>{metric(model.validation_metrics.roc_auc)}</td>
                          <td>{percentage(model.grouped_majority_baseline.accuracy)}</td>
                          <td>{percentage(model.accuracy_delta_vs_grouped_majority_baseline)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="ml-performance-warning">
                  These grouped results are near chance on this dataset; none
                  demonstrated useful predictive skill over the grouped majority
                  baseline. Scores are descriptive of six runs only.
                </p>
                <div className="ml-secondary-metrics">
                  <span>
                    Selected-model Brier score:{" "}
                    <b>{metric(selectedModel.validation_metrics.calibration.brier_score)}</b>
                  </span>
                  <span>
                    Expected calibration error:{" "}
                    <b>{metric(selectedModel.validation_metrics.calibration.expected_calibration_error)}</b>
                  </span>
                  <span>{selectedModel.validation_metrics.calibration.status.replaceAll("_", " ")}</span>
                </div>
              </>
            )}
          </section>

          {selectedModel && (
            <div className="ml-analysis-grid">
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <p className="eyebrow">OUT-OF-FOLD DIAGNOSTICS</p>
                    <h2>Confusion matrix &amp; ROC</h2>
                    <p>Every prediction is generated with the entire target RunID held out.</p>
                  </div>
                </div>
                <MlConfusionRocChart metrics={selectedModel.validation_metrics} theme={theme} />
              </section>
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <p className="eyebrow">MODEL-AGNOSTIC EXPLANATION</p>
                    <h2>Global Shapley summary</h2>
                    <p>
                      {explanationLoading
                        ? "Loading exact empirical Shapley values…"
                        : "Mean absolute contribution to the model score; not a causal effect."}
                    </p>
                  </div>
                </div>
                {explanationError
                  ? <div className="ml-inline-error" role="alert">{explanationError}</div>
                  : <MlShapFeatureChart items={explanation} theme={theme} />}
              </section>
            </div>
          )}

          {selectedModel && (
            <section className="panel ml-inference-panel">
              <div className="panel-head">
                <div>
                  <p className="eyebrow">EXPLORATORY INPUT TESTER</p>
                  <h2>Score an independent-sensor cycle</h2>
                  <p>
                    Enter values in the exact units shown. Blank channels use
                    training-only median imputation and are listed in the result.
                  </p>
                </div>
                <label className="ml-model-select">
                  <span>Model version</span>
                  <select
                    value={selectedModelId}
                    onChange={(event) => {
                      setSelectedModelId(event.target.value);
                      setPrediction(null);
                      setPredictionError("");
                    }}
                  >
                    {models.map((model) => (
                      <option key={model.model_id} value={model.model_id}>
                        {model.display_name} · v{model.version}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <form className="ml-inference-form" onSubmit={submitPrediction}>
                <div className="ml-inference-fields">
                  {FEATURE_INPUTS.map((feature) => (
                    <label className="field" key={feature.name}>
                      <span>{feature.label}</span>
                      <input
                        type="number"
                        step="any"
                        value={featureValues[feature.name] ?? ""}
                        onChange={(event) => {
                          setFeatureValues((current) => ({
                            ...current,
                            [feature.name]: event.target.value,
                          }));
                        }}
                        aria-label={`${feature.label}, ${feature.unit}`}
                      />
                      <small>{feature.unit}</small>
                    </label>
                  ))}
                </div>
                <input type="hidden" name="model_id" value={selectedModelId} />
                <button className="button primary" type="submit" disabled={predictionLoading}>
                  {predictionLoading ? "Scoring…" : "Run exploratory inference"}
                </button>
              </form>

              {predictionError && <div className="ml-inline-error" role="alert">{predictionError}</div>}
              {prediction && (
                <div className="ml-prediction-result" role="status">
                  <div className="ml-prediction-heading">
                    <span>Predicted archived band</span>
                    <strong>{prediction.prediction.predicted_class}</strong>
                    <b>{prediction.prediction.confidence_pct.toFixed(1)}% model score</b>
                  </div>
                  <div className="ml-class-probabilities">
                    {Object.entries(prediction.prediction.class_probabilities).map(([label, probability]) => (
                      <span key={label}>{label}: {percentage(probability)}</span>
                    ))}
                    <span>Predictive entropy: {prediction.prediction.predictive_entropy_bits.toFixed(3)} bits</span>
                  </div>
                  {prediction.prediction.imputed_features.length > 0 && (
                    <p>
                      Median-imputed inputs:{" "}
                      {prediction.prediction.imputed_features
                        .map((name) => FEATURE_INPUTS.find((feature) => feature.name === name)?.label ?? name)
                        .join(", ")}
                    </p>
                  )}
                  <p className="ml-safety-disclaimer">{prediction.safety_disclaimer}</p>
                </div>
              )}
            </section>
          )}

          <p className="ml-artifact-note">
            Artifacts use a versioned, non-executable JSON format and remain within this project
            because redistribution terms for the contributing raw PSI-101 files
            have not been established. Feature units are validated at inference.
          </p>
        </>
      )}
    </div>
  );
}
