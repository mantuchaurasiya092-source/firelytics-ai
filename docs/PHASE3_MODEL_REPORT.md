# Phase 3 — Grouped PSI-101 Model Development Report

**Inspection/training date:** 2026-11-15  
**Status:** The existing local model artifacts have been restored and verified end to end through FastAPI and the Next.js proxy. Frontend typecheck/build pass using the repository-bundled Node.js 22 runtime. The artifacts remain git-ignored; production availability is not established because raw-file and derivative-model distribution rights are unverified and no approved artifact store is configured. This is not a validated fire classifier.

## 1. Scope and target

Phase 3 trains only the narrow Phase 2 Task 6 target: binary prediction of the archived `ObservedBand` label from the PSI-101 SAME-R cycle ledger. The two target classes are `10000-14999` and `20000+`; 14 `MixedBand` cycles are excluded. The resulting data contains **7,886 labeled cycles**: class 0 = 3,946 and class 1 = 3,940, across RunIDs 63, 64, 76, 84, 95, and 97.

`ObservedBand` is a historical band derived from DustTrak-A measurements. It is not a label for fire/no-fire, ignition, extinction, smoke-versus-dust, or nuisance-dust outcomes. These models must not be presented as any of those classifiers.

## 2. Feature construction and leakage controls

The training loader joins the backend-bundled cycle sequence to locally present raw rows using the cycle ledger's `RunID` and `SourceDataRows`. It calculates the median of each independent sensor channel within a cycle:

| Model input | Source column | Unit |
|---|---|---|
| DustTrak B mass concentration | `DustTrakBMeasurement(MgPerM3)` | mg/m³ |
| P-Trak particle number concentration | `PTrakMeasurement(PtPerCC)` | particles/cm³ |
| Gas plume temperature | `GasPlumeTemperature(DegC)` | °C |
| Sample heater resistance | `SampleResistance(Ohms)` | Ω |
| MFC mass flow rate | `MFCMassFlowRate(LPM)` | L/min |

The target-generating DustTrak-A mass and analog channels, `ObservedBand`, `ExpectedBand`, `RelativeCyclePhase`, `ExceptionIndicator`, mixed-band indicators, duplicate flags, and `RunID` are not model features. `-999` sentinels are treated as missing. Median imputation is fitted inside each training fold only; the logistic regression scaler is also fitted inside each fold. A fold's test RunID is never included in its training partition.

The 25 archive cycles carrying `DuplicateCycleIndicator=1` remain single cycle records; their multiple `SourceDataRows` are reduced to the same per-cycle sensor medians. The feature data comes from workspace-local raw files; the trained JSON artifacts are therefore **kept local** pending review of raw-file and derivative-model redistribution terms.

## 3. Evaluation design

All reported metrics are pooled out-of-fold predictions from six Leave-One-RunID-Out folds. Each of the six runs is held out once, with the other five used for training. Group overlap is asserted to be zero in every fold. The final model files are subsequently refit on all six groups for local interactive inference; the reported validation metrics are not in-sample metrics from those final fits.

The grouped majority baseline predicts the training-fold majority class for each held-out run. No threshold or hyperparameter tuning used the held-out predictions. Models are deterministic, with fixed seeds:

- Logistic Regression with training-fold median imputation and standard scaling.
- Random Forest (100 trees, max depth 8, minimum leaf size 5).
- Gradient Boosting (100 estimators, learning rate 0.05, depth 2, minimum leaf size 5).

## 4. Measured grouped validation results

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | ECE | Grouped majority accuracy | Accuracy delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.498225 | 0.496957 | 0.352284 | 0.412298 | 0.498932 | 0.250007 | 0.003076 | 0.500380 | -0.002155 |
| Random Forest | 0.498098 | 0.497525 | 0.459137 | 0.477561 | 0.498350 | 0.250647 | 0.016734 | 0.500380 | -0.002282 |
| Gradient Boosting | 0.501014 | 0.500884 | 0.359391 | 0.418502 | 0.496687 | 0.251024 | 0.008710 | 0.500380 | +0.000634 |

These are near-chance results. ROC-AUC is approximately 0.5 and no model shows useful improvement over the grouped baseline. **The evaluation does not support a predictive-skill claim.** Per-run accuracies are also near 0.5; their exact values are returned in `GET /ml/models`.

The API reports a 0.5 decision threshold, out-of-fold confusion matrix, and ROC points. Brier score and 10-bin expected calibration error (ECE) are diagnostics only. Prediction `confidence` is the maximum model class probability, and entropy is a score of output dispersion; neither is a calibrated confidence interval or safety probability.

## 5. Explainability

`backend/ml/explainability/explainer.py` calculates exact model-agnostic interventional Shapley values by enumerating the five-feature coalitions over a deterministic empirical background sample (32 background rows; up to 64 rows explained). Summaries report mean absolute and signed contributions to predicted probability of the `20000+` observed-band class.

These global summaries explain the fitted model's behavior on its training-row sample; they are not causal effects, physical attribution, held-out-run explanations, or evidence that a sensor is a fire detector. Native tree importance or absolute standardized logistic coefficients are returned separately and clearly identify their importance basis.

## 6. Artifact and API behavior

The offline training command is `python -m ml.training.trainer` from the `backend/` directory after installing the optional `.[ml]` extra (`scikit-learn>=1.8,<2`). It writes versioned JSON estimator parameters, validation results, provenance, and explanations beneath `backend/ml/models/artifacts/`. These are non-executable JSON, not pickle/joblib files, and are ignored by Git because the source raw files and derivative redistribution terms have not been cleared. The runtime loader expects `backend/ml/models/artifacts/registry.json`; it does not train automatically. The three model artifacts and registry are available in this local checkout only.

The FastAPI router exposes:

- `GET /ml/models` and `/api/ml/models` — versions, grouped metrics, majority baseline, ROC data, and limitations.
- `POST /ml/predict` and `/api/ml/predict` — accepts only the declared five feature names with exact units; `null` values are training-median imputed and reported. The response includes class probabilities, model-score confidence, predictive entropy, and the scientific disclaimer.
- `GET /ml/explainability/{model_id}` and `/api/ml/explainability/{model_id}` — global feature importance and Shapley summaries.

If local artifacts are absent, the model endpoints return an explicit service-unavailable error; they do not train on startup or substitute fabricated model results. The dataset feasibility endpoint reports whether local Task 6 artifacts exist. The JSON files are ignored by Git (`backend/ml/models/.gitignore`), so Git-based Vercel deployments do not receive them. Production inference requires an approved artifact packaging or external-storage plan after file and derivative-use rights are confirmed.

## 7. Frontend

The **ML · FIRE RESEARCH LAB** tab is added alongside existing workspaces. It fetches the model registry and explainability through the existing same-origin proxy, shows all three algorithms and their grouped validation metrics, renders an SVG confusion matrix and ROC curve, charts the top five Shapley features, and provides a unit-checked sensor-input form. The workspace states that results are exploratory and that the observed-band target is not a fire or dust classification. Chart text uses pure white/dark-mode or pure black/light-mode colors, with colored scientific marks.

## 8. Source files

- Dataset and model assembly: `backend/ml/training/trainer.py`
- Evaluation and calibration diagnostics: `backend/ml/evaluation/metrics.py`
- Exact empirical Shapley summaries: `backend/ml/explainability/explainer.py`
- Safe portable inference: `backend/ml/models/runtime.py`
- API routes: `backend/ml/router.py`, mounted by `backend/app/main.py`
- Frontend types/workspace/charts: `frontend/app/ui/model.ts`, `frontend/app/ui/ml-fire-research-lab.tsx`, `frontend/app/ui/charts.tsx`, `frontend/app/ui/dashboard.tsx`, `frontend/app/globals.css`
- API, metrics, and Shapley tests: `backend/tests/test_api.py`

## 9. Artifact status and deployment boundary

- Existing local artifacts were checked against SHA-256 hashes for the bundled cycle ledger and the six raw training CSVs; all seven hashes match. Artifacts were not regenerated during this verification.
- Artifact sizes at verification: `registry.json` 343,259 bytes; `logistic_regression_v1_0_0.json` 112,200 bytes; `gradient_boosting_v1_0_0.json` 166,098 bytes; `random_forest_v1_0_0.json` 2,124,120 bytes.
- Scikit-learn and NumPy are not installed in `.venv-local`; API loading/inference uses the safe JSON runtime and does not require the training extra. Training itself requires the `.[ml]` optional group.
- The raw source CSVs and model artifact JSONs are excluded by Git ignore rules. `vercel.json` configures a backend service but no model artifact binding, external storage, or build-time artifact provisioning. No deployed Vercel URL was supplied or verified; production model availability must not be inferred from local results.

## 10. Validation

- `python -m pytest -q`: **41 passed** after adding a regression test for the truthful missing-registry 503 response (one Starlette TestClient deprecation warning).
- Live local `/health`, `/ml/models`, `/api/ml/models`, `/api/ml/datasets`, and all three `/ml/explainability/{model_id}` requests returned HTTP 200.
- A unit-correct browser submission through the Next.js proxy returned HTTP 200 and rendered the result using the selected local model. The probe value was entered solely to exercise the inference path; it is not a PSI-101 observation or scientific finding.
- All three registry models report 7,886 out-of-fold predictions over six Leave-One-RunID-Out groups; artifact fold metadata contains no held-out RunID overlap, and the saved input hashes match the current local sources.
- Frontend `npm run typecheck` and `npm run build` passed using bundled Node.js 22.23.5/npm and the existing dependencies.
- Direct and proxied digital-twin and decision-support routes also returned successful responses. The initial browser navigation recorded transient aborted requests while services were starting; after startup, the ML registry, explainability, and prediction requests succeeded. Browser logs also contain pre-existing SVG `height="auto"` console errors outside the ML workspace.

