# FIRELYTICS AI — Project Progress

## Mission
Build an evidence-grounded, software-only NASA microgravity combustion research and decision-support platform.

## Current Phase
**Phase 1 — Local Ollama AI Research Agent & Scientific RAG: complete.**
**Phase 2 — NASA Dataset Discovery, Ingestion & Quality Assessment: complete.**
**Phase 3 — ML Model Development, Training, SHAP Explainability & ML Fire Research Lab: complete.**
**Phase 4 — Virtual Spacecraft Monitoring & Anomaly Detection: complete.**
**Phase 5 — Fire Suppression & Mitigation Digital Twin: complete.**
**Phase 6 — Scientific Decision Support Integration: complete.**
**Phase 7 — Testing, Validation, Documentation & Deployment Readiness: local verification complete; production artifact delivery remains rights-gated.**

## Completed
- Phase 0 repository audit: `docs/ADVANCED_IMPLEMENTATION_AUDIT.md`.
- Phase 1 `backend/ai/` package with local Ollama HTTP client, deterministic chunking and TF-IDF/cosine retrieval, source filters/citations, constrained prompts, and all 13 task modes.
- Mounted `/ai/*` and `/api/ai/*` status, retrieval, chat, simulation-explanation, report, and session-history routes without changing existing scientific endpoints.
- Added the sixth **AI · SCIENTIFIC RESEARCH ASSISTANT** workspace with local model/status controls, direct document retrieval, chat/history, six quick actions, source citations, and four-tier epistemic cards.
- Added unsupported citation-ID, DOI, and numeric-value filtering for local model text. Scientific interpretations still require human review.
- No paid APIs, new packages, hardware interfaces, or raw NASA data ingestion were added.
- Added `backend/ml/datasets/` registry/loaders, grouped preprocessing/splitting, causal feature engineering, and read-only `/ml/*` plus `/api/ml/*` dataset/task/quality routes.
- Added Phase 2 quality report and task feasibility assessment. Tasks 1–4 are not trainable from local raw labels; Task 5 is exploratory; Task 6 is narrowly feasible for bundled DustTrak-A band/phase-exception labels grouped by RunID. No model was trained.
- The registry inspected 14 Tier-1 catalogue records, 10 Tier-2 scope records, seven raw PSI-101 run CSVs (10,350 rows), nine backend metadata CSVs, 50 workspace metadata CSVs, two quarantined duplicate CSVs, and 7,900 bundled cycle rows across six reconciled runs.
- DataCite verification found 12 matching DOI records; the PSI-20 catalogue DOI returned 404 and PSI-22 remains pending. The suggested PSI-101 DOI `10.60555/037m-9382` returned 404; use the verified catalogue DOI `10.60555/2np7-jv14`.
- Added grouped Leave-One-RunID-Out baseline training for the narrow archived `ObservedBand` label. The three models use 7,886 labeled cycles across Runs 63, 64, 76, 84, 95, and 97; no target-generating DustTrak-A channels or archive labels are predictors.
- Evaluated Logistic Regression, Random Forest, and Gradient Boosting against the grouped-majority baseline. Results are near chance (accuracy 0.4981–0.5010, ROC-AUC 0.4967–0.4989) and do not support useful predictive skill or any fire/ignition/smoke classification claim.
- Added safe JSON-only model artifacts, grouped metrics/calibration diagnostics, exact empirical interventional Shapley summaries, `/ml/models`, `/ml/predict`, and `/ml/explainability` routes, and the **ML · FIRE RESEARCH LAB** workspace. Generated artifacts are local-only pending data/derivative redistribution review.
- Added `backend/telemetry/` with seven deterministic, explicitly synthetic scenarios; a 1 Hz HTTP-polling stream capped at 60 frames; local PSI-101 raw replay for the six reconciled runs; bounded CSV upload/replay; and rule-based plus rolling z-score alerts with no confidence scores.
- Mounted `/telemetry/mode`, `/telemetry/stream`, and `/telemetry/upload` with `/api/telemetry/*` aliases. Added the **VIRTUAL SPACECRAFT MONITORING** workspace, synchronized SVG temperature/O₂/airflow tracks, source labels, and a severity-coded alert timeline. HTTP polling was chosen because the existing Next proxy does not handle WebSocket upgrades.
- PSI-101 replay maps only source-compatible measurements: measured gas-plume temperature and separately named aerosol/instrument channels. O₂, cabin pressure, cm/s airflow, gravity, and smoke-specific values stay null because those data are not recorded in the local raw files. User CSVs are explicitly unverified.
- Added `backend/digital_twin/` schemas, a deterministic boundary-condition scenario interpolator, and `/digital-twin/simulate` plus `/api/digital-twin/simulate`. Ventilation cutoff, user-targeted depressurization/O₂ vitiation, inert-gas O₂ boundary scenarios, and gravity shifts compare paired trajectories without a hardware command path.
- The Phase 5 engine does not model flame temperature/volume response, MOC, heat transfer, extinction, or CO₂/helium effectiveness. Temperature and flame volume are pass-through context or unknown. PSI-25 BASS-II, PSI-69 FLEX, and PSI-98 SAFFIRE-I are cited as contextual catalogue references only; their raw outcome tables are not locally available. Numerical uncertainty margins are explicitly unquantified.
- Added the **FIRE SUPPRESSION DIGITAL TWIN** workspace with a two-sided scenario form, O₂ boundary-condition comparison chart, read-only assumptions/references, and persistent no-actuation safety disclaimer.
- Added `backend/decision_support/` with strict scenario inputs, state aggregation, deterministic research-brief synthesis, local PSI catalogue ranking, and RAG citation retrieval. Mounted `/decision-support/synthesize` and `/api/decision-support/synthesize`.
- Added the **SCIENTIFIC DECISION SUPPORT** workspace: active scenario context, a two-by-two catalogue/physics, telemetry/ML, twin, and RAG/evidence-gap view, caller-provided snapshot disclosures, epistemic separation, subsystem-unavailable warnings, and Markdown export.
- Decision support does not invoke an LLM or produce recommendations. LLM suggestions are explicitly `not_generated`; telemetry, ML and twin payloads remain caller-provided and unverified, and no alerts do not imply safety. The dashboard reads current telemetry and grouped model registry snapshots, and retains the latest twin result in browser session storage for this workspace.
- Added the Windows one-click `start-firelytics.bat` wrapper for the existing launcher, added Uvicorn to `backend/requirements.txt` for the documented backend quickstart, and aligned README/about startup instructions and team credits with the Developer modal.
- Added a FastAPI route-registration test covering standard and `/api/...` aliases across all Phase 1–6 feature routers. Updated the release docs with current workspace count, PSI scope, safety-principles links, and explicit verification caveats.
- The existing local model artifacts are present at `backend/ml/models/artifacts/`; their seven recorded source SHA-256 hashes match the bundled cycle ledger and six selected raw-run CSVs. They were not regenerated during this check because raw-file and derivative-model permissions remain unverified. The model JSON and raw CSVs remain Git-ignored.
- Clarified the 503 message and ML workspace copy: deployment artifacts are intentionally absent from Git, and local retraining is an explicit, rights-dependent operation rather than an API fallback.

## Dataset Status
- The project catalogue contains 14 Tier-1 NASA PSI metadata records and 10 Tier-2 scope entries; the multi-investigation records remain condition envelopes rather than locally downloaded raw trial tables.
- Packaged PSI-101/SAME-R archive summaries cover six Pyrell runs. Phase 4 raw replay reads only locally present reconciled runs; raw CSVs remain outside the deployment bundle, so replay is not available in a clean deployment without separately approved data provisioning.
- Local raw files are not included in the backend deployment bundle. Quarantined Run107-labeled files are exact byte/hash duplicates of Runs 95 and 97 and are excluded as independent experiments.
- Local PSI-101 raw files remain subject to per-file redistribution review. The AI corpus excludes raw experiment CSVs.
- No physical sensors, device drivers, or hardware control paths are implemented.

## Architecture
Next.js dashboard → same-origin Next API proxy → FastAPI. The telemetry router uses bounded HTTP polling rather than WebSockets and keeps one process-local stream state. The digital twin is a stateless, explicitly uncalibrated scenario interpolator; it estimates only user-specified environmental boundary conditions. It does not predict fire behavior or issue physical commands. Scientific decision support reuses the catalogue ranking and physics surrogate, retrieves local RAG citations, and deterministically separates inputs, calculated surrogates, and absent LLM suggestions. Ollama inference is optional at `OLLAMA_BASE_URL` (default `http://127.0.0.1:11434`). Conversation history is session-keyed in process and mirrored in browser `localStorage`. Ollama embeddings are opt-in; lexical retrieval works without external packages or a running model.

## Validation
- `python -m pytest -q`: **41 passed**, with one Starlette TestClient deprecation warning.
- Verified the three existing local artifacts use 7,886 out-of-fold predictions over six RunIDs, with no held-out RunID overlap and all 14 mixed-band cycles excluded. Model metrics and artifact hashes are recorded in `docs/PHASE3_MODEL_REPORT.md`.
- Frontend `typecheck` and production `build` both passed using repository-bundled Node.js 22.23.5/npm and existing frontend dependencies; Node/npm/npx are not on PATH. No dependency installation was needed.
- Local direct and proxied requests returned HTTP 200 for health, both ML registry aliases, dataset registry, all model explainability routes, telemetry stream, and successful twin/decision-support requests. Browser-selected Random Forest explanation and an exploratory prediction submission rendered successfully.
- Live `GET /api/ai/status` was verified to return online with `qwen3:4b` available and selected.
- Offline deterministic retrieval, API fallback, dataset endpoints, grouped split leakage checks, and causal feature behavior are covered by tests. Live Ollama generation, persistent history across backend restarts, and optional embedding/FAISS retrieval remain unverified.
- FAISS is not installed. No model was downloaded and no dependency was added in Phase 2.

## Remaining Limitations
- Prompts and citation/value sanitization do not prove semantic correctness; verify generated statements against cited primary sources.
- The in-memory RAG index and backend history are not persistent. Ollama must be hosted separately from Vercel for local inference.
- Phase 4 provides software-generated and local replay telemetry only; there is no live sensor feed, hardware, driver, or command path. Phase 5 compares scenario boundary conditions only; no locally calibrated suppression model, flame-response model, or numeric uncertainty interval exists. Phase 6 caller-provided telemetry/ML/twin results are not independently validated by its aggregator. The local Phase 3 model artifacts and raw replay CSVs are not bundled for deployment.
- Metadata for many PSI investigations is available, but structured local measurement tables remain limited to the inspected PSI-101 subset.

## Release Gate
Local ML functionality is verified. Production ML functionality is **not** verified: JSON models are git-ignored, PSI-101 raw data is git-ignored, and file-level/derived-model redistribution rights are unconfirmed. Keep that unavailable state explicit until rights are cleared and an approved model delivery/storage path is configured and tested in the deployment. Keep telemetry alerts, the digital twin, and decision-support summaries exploratory; preserve provenance and units; and do not add physical control paths or present scenario outputs as operational recommendations.
