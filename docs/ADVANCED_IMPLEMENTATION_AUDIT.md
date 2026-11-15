# Advanced Implementation Audit — Phase 0 through Phase 7

- **Project:** FIRELYTICS AI — Flame in Freefall
- **Audit scope:** Repository documentation, application code, manifests, tests, and locally present PSI-101 data.
- **Change boundary:** Phase 0 was documentation-only. Phases 1 and 2 added the local AI and dataset-inspection/preprocessing modules, API routes, focused tests, and directly related documentation. No dependency manifest or runtime dependency was added.

**Release status:** Local Phase 7 verification is complete: backend/root tests, frontend typecheck/build, local model registry/inference, and standard/`/api` route aliases pass. Production ML availability remains unverified and is not claimed: model JSON and PSI-101 raw files are git-ignored pending rights review, and no approved external artifact store or deployment binding exists.

**Evidence and scope notes**

This audit distinguishes executable behavior from documentation claims and from files merely present in the workspace. Source references use repository-relative paths and line numbers where applicable; CSV references point to the named file and its header/data rows. The NASA PSI identifiers and DOI values below are the ones represented in the local catalogue and references; they should not be read as a claim that every public PSI file was downloaded.

The Phase 1 request supplied the exact Part 3 candidate tasks and Part 9 safety principles; both lists are reproduced verbatim in Sections 8 and 12. This document began as the Phase 0 repository audit. The Phase 2 dataset inspection supersedes the earlier local-data and task-feasibility statements in Sections 5 and 7–9.

### Phase 1 implementation status

- Added `backend/ai/` with an Ollama standard-library HTTP client, deterministic provenance-aware document chunker, zero-dependency TF-IDF/cosine index, optional opt-in Ollama embeddings and optional FAISS acceleration, metadata-filtered retrieval, constrained prompts, a 13-mode research agent, and a modular FastAPI router.
- Mounted `/ai/*` and `/api/ai/*` status, retrieval, chat, simulation-explanation, report, and history routes without changing existing scientific endpoints. The Next same-origin proxy now also forwards DELETE for session-history clearing.
- Added the sixth **AI · SCIENTIFIC RESEARCH ASSISTANT** workspace with model/status controls, direct corpus search, local chat/history, six quick actions, citations, and four-tier epistemic cards. No paid API or package dependency was added.
- Verification: `python -m pytest -q` — **16 passed** (one Starlette TestClient deprecation warning); TypeScript check passed; Next.js production build passed. `node`/`npm`/`npx` were not on PATH, so the existing local TypeScript and Next.js runners were invoked using the Node runtime bundled with Cursor.
- Limitations: the local Ollama daemon responds to status and `/api/ai/status` reports `qwen3:4b` installed and selected; a live generation was not tested in this phase. FAISS is not installed; optional embeddings/FAISS are not required and embeddings are disabled by default. The lexical index is built in process and is not persistent. Citation/DOI and unsupported numeric-string filtering reduce unsupported output, but cannot prove every semantic LLM statement true; source review remains mandatory.

**Phase 1 sources:** `backend/ai/ollama/client.py` (`OllamaClient`); `backend/ai/rag/chunker.py` (`chunk_document`); `backend/ai/rag/indexer.py` (`build_corpus`, `HybridIndex`, `get_index`); `backend/ai/retrieval/retriever.py` (`Retriever`); `backend/ai/prompts/templates.py` (`SYSTEM_PROMPT`); `backend/ai/agents/research_agent.py` (`ResearchAgent`); `backend/ai/router.py`; `frontend/app/ui/ai-research-assistant.tsx`; `backend/tests/test_api.py`.

### Phase 2 implementation status

- Added `backend/ml/datasets/` with an on-disk PSI-101/catalogue registry, SHA-256 provenance, exact CSV schemas, units, row/missing/sentinel/class statistics, deployment availability, DOI verification snapshot, and structured task feasibility assessments.
- Added reproducible local loaders, `RunID`-grouped holdout/GroupKFold/Leave-One-Group-Out splits, train-only median imputation and unit-checked scaling, and causal telemetry/cycle feature engineering. No external data was fetched and no model was trained.
- Mounted read-only `/ml/datasets`, `/ml/tasks`, and `/ml/datasets/{dataset_id}/quality` routes with `/api` aliases.
- Local inventory: 14 Tier-1 catalogue records; 10 Tier-2 scope records; seven raw PSI-101 CSV runs (10,350 rows); 9 backend metadata CSVs; 50 workspace metadata CSVs; two quarantined CSVs verified as exact duplicates of Runs 95 and 97; 7,900 bundled cycle records across six reconciled RunIDs.
- Verification: `python -m pytest -q` passed **21 tests** (one Starlette deprecation warning); live `GET /api/ai/status` returned HTTP 200 with `online=true`, `available_models=["qwen3:4b"]`, and `selected_model="qwen3:4b"`. The Phase 2 TypeScript/build commands could not run because `npx`/`npm` and a Node executable were unavailable in this shell; no dependencies were installed.

**Phase 2 sources:** `backend/ml/datasets/registry.py`; `backend/ml/datasets/loader.py`; `backend/ml/preprocessing/pipeline.py`; `backend/ml/features/engineering.py`; `backend/ml/router.py`; `backend/app/main.py`; `backend/tests/test_api.py`; `docs/PHASE2_DATASET_QUALITY_REPORT.md`.

## 1. Current Application Architecture

### Deployed application and request flow

- `frontend/app/page.tsx` renders one client workbench (`Home` returns `Dashboard`); it does not mount a second dashboard. The frontend is Next.js 16.4.6, React 19.3.1, and TypeScript 5.9.3, with Node constrained to 22.x in `frontend/package.json`.
- The browser calls the same-origin Next Route Handler at `/api/backend/*`. `frontend/app/api/backend/[...path]/route.ts` reads the server-only `BACKEND_URL`, validates the path, forwards **GET, POST, and DELETE** requests to the private FastAPI service, and preserves selected response headers. A missing binding returns 503, an invalid path 400, and a failed backend fetch 502. The handler does not implement a WebSocket upgrade proxy.
- Root `vercel.json` declares separate `backend/` (FastAPI, entrypoint `app.main:app`) and `frontend/` (Next.js) services, binds the backend service URL as `BACKEND_URL`, and routes public traffic to the frontend. This is configuration, not proof of a current cloud deployment.
- `frontend/app/ui/dashboard.tsx` owns client state. Its initial effect requests investigations, SAME-R runs, health, habitat profiles, and repository scope in parallel. Later effects load a selected record, selected run summary and validation, and comparison results; simulation, ranking, cycle lookup, and report downloads are separate actions. AbortControllers cancel stale requests. The browser does not call FastAPI directly.
- `backend/app/main.py` creates one FastAPI `app`, mounts the AI, ML, telemetry, digital-twin, and decision-support routers, and retains core catalogue/archive handlers in the module. Each feature router exposes standard and `/api/...` aliases. Inputs use Pydantic request models. Catalogue loading is cached.
- The AI workspace owns its local chat/model/filter/retriever state in `frontend/app/ui/ai-research-assistant.tsx`; the existing shared catalogue, scenario, simulation, and comparison state is passed in from the dashboard.
- The legacy `app/streamlit_app.py` remains a local six-tab application. It imports the root `src/` modules, which provide compatibility with the canonical backend catalogue/reporting code, while `src/samer.py` and `recover_phase_lineage.py` replay locally available raw PSI-101 rows.
- Production SAME-R is not raw replay: `backend/app/archive.py:get_archive()` loads nine packaged metadata CSVs, validates archived count/identity checkpoints, and sets `raw_replay_performed` to false. The root analysis is a separate local raw-data path. Reports are generated in memory; AI history is stored in browser `localStorage` and process memory, with no server database.

**Sources:** `frontend/app/page.tsx`; `frontend/package.json`; `frontend/app/api/backend/[...path]/route.ts`; `vercel.json`; `frontend/app/ui/dashboard.tsx`; `frontend/app/ui/ai-research-assistant.tsx`; `backend/app/main.py`; `backend/ai/router.py`; `backend/app/archive.py`; `app/streamlit_app.py`; `src/catalogue.py`; `src/samer.py`; `docs/architecture.md`; `docs/vercel-migration.md`.

### Implemented FastAPI paths

| Method | Backend path | Verified purpose |
|---|---|---|
| GET | `/health` | Service, catalogue count, archive validation, and raw-replay availability |
| GET | `/investigations` | Catalogue plus repository scope |
| GET | `/investigations/{investigation_id}` | One catalogue record |
| GET | `/repository/scope`, `/api/repository/scope` | 24-study scope accounting |
| GET | `/habitats`, `/api/habitats` | Five screening profiles |
| POST | `/scenarios/rank` | Deterministic catalogue evidence ranking |
| POST | `/simulate`, `/api/simulate` | Screening surrogate, ranked evidence, and synthesis |
| POST | `/compare`, `/api/compare` | Comparison matrix and metadata synthesis |
| GET | `/samer/runs` | Six archived run summaries |
| GET | `/samer/runs/{run_id}/validation` | Archived-output reconciliation checks |
| GET | `/samer/runs/{run_id}/summary` | Archived phase, lag, model, and exception products |
| GET | `/samer/runs/{run_id}/cycles/{cycle_id}` | Archived cycle and source-row references only |
| POST | `/reports/csv`, `/reports/html` | In-memory report attachments |
| GET | `/ai/status`, `/api/ai/status` | Local Ollama status/model recommendations and RAG corpus statistics |
| POST | `/ai/retrieve`, `/api/ai/retrieve` | Filtered local TF-IDF retrieval with exact excerpts and source metadata |
| POST | `/ai/chat`, `/api/ai/chat` | One of 13 research task modes, citations, and epistemic breakdown |
| POST | `/ai/explain-simulation`, `/api/ai/explain-simulation` | Explanation of supplied screening inputs/outputs; does not recompute them |
| POST | `/ai/generate-report`, `/api/ai/generate-report` | Structured report or exploratory proposal |
| GET/DELETE | `/ai/history`, `/api/ai/history` | Process-local, session-keyed history retrieval/clearing |
| GET/POST | `/ml/*`, `/api/ml/*` | Dataset/task registry, model metrics, prediction, and explainability |
| GET/POST | `/telemetry/*`, `/api/telemetry/*` | Synthetic/replay mode, bounded stream, upload, and anomaly log |
| POST | `/digital-twin/simulate`, `/api/digital-twin/simulate` | Exploratory environment-boundary comparison |
| POST | `/decision-support/synthesize`, `/api/decision-support/synthesize` | Deterministic evidence-linked research brief |

There are no backend `/api/health`, `/api/catalogue`, or `/api/rank` paths. The `/api/backend/` prefix belongs to the Next proxy, not to the underlying FastAPI route. **Sources:** `backend/app/main.py`; `backend/ai/router.py`; `frontend/app/api/backend/[...path]/route.ts`; `README.md:369-388`.

### Documentation cross-check

- `docs/architecture.md` and `docs/vercel-migration.md` correctly describe the two-service/private-backend design, but the architecture document's phrase “four native responsive SVG charts” is not a literal description of all four labeled visualizations: Chart C is DOM/HTML, Chart D contains two SVG plots, and the smoke-versus-dust SVG panel is an additional unnumbered visualization.
- `docs/methodology.md` and `docs/references.md` describe a metadata-led catalogue, a six-run SAME-R archive, and a non-validated visualization surrogate. `README.md` counts 13 non-pending DOI strings; Phase 2 DataCite checks verified 12, returned 404 for the PSI-20 string, and found PSI-22 pending.
- `docs/architecture.md:52` describes all 14 records as DOI-linked; this conflicts with the catalogue, README, and references, which identify only 13 DOI values and a pending PSI-22 DOI.
- `docs/validation.md:7` and `docs/vercel-migration.md:92` retain pre-Phase-1 test-count descriptions; current validation is summarized in `progress.md`.
- `docs/dataset_inspection_report.md` reports an inspection of `D:\DATASETS 2` and a nine-file metadata/PDF directory. That is a different inspection scope from the current repository's `data/raw/PSI-101/Pyrell/`, which contains seven CSVs and three PDF/PPTX files. The former report should not be used to claim that the current repository has no measurements.
- `DECISIONS.md` still marks Streamlit as a proposed dashboard and the AI provider as pending; these are stale status records rather than descriptions of the current application. `progress.md` records Phase 7 repository hardening and the remaining frontend/deployment verification gate.

**Sources:** `docs/architecture.md:26-89`; `docs/methodology.md:1-122`; `docs/validation.md:1-64`; `docs/references.md:1-28`; `docs/dataset_inspection_report.md:1-14, 179-205`; `docs/vercel-migration.md:1-94`; `README.md:1-27, 463-484`; `DECISIONS.md:1-45`; `progress.md:1-73`.

## 2. Verified Implemented Features

### Workspaces and frontend state

`frontend/app/ui/model.ts` defines ten tab IDs and labels:

1. **Mission & Habitat Simulator**
2. **Catalogue & Comparison Matrix**
3. **SI Fire-Safety Synthesis**
4. **PSI-101 SAME-R Telemetry & Lineage**
5. **All-in-One Executive View** (the code label corresponding to the requested “Executive View”)
6. **AI · SCIENTIFIC RESEARCH ASSISTANT**
7. **ML · FIRE RESEARCH LAB**
8. **VIRTUAL SPACECRAFT MONITORING**
9. **FIRE SUPPRESSION DIGITAL TWIN**
10. **SCIENTIFIC DECISION SUPPORT**

The executive view composes the first four research workspaces and methods content rather than being an independent backend service. The AI workspace provides Ollama/offline status, local model selection, all 13 task modes, six quick actions, session-keyed history, direct source retrieval, four epistemic cards, and source citations. The dashboard also includes grouped ML evaluation, synthetic/replay telemetry, the exploratory boundary-condition twin, decision-support synthesis, a collapsible 24-investigation scope matrix, five habitat presets, search/filter/sort, comparison of 2–4 records, selectable archived runs, cycle reference lookup, dark/light theme, and the Developer modal.

**Sources:** `frontend/app/ui/model.ts` (`TabId`, `TABS`); `frontend/app/ui/dashboard.tsx` (`showAiAssistant` and conditional render); `frontend/app/ui/ai-research-assistant.tsx`; `docs/architecture.md:26-77`.

### Charts and evidence visualizations

- **Chart A — O2/pressure envelope:** native SVG plot of the boundary, screening points, and habitat markers.
- **Chart B — partial-gravity bounding:** native SVG plot of the MOC/spread surrogate and the illustrative E-FIELD scale.
- **Chart C — ranked evidence breakdown:** factor strips and score/coverage/proximity tracks rendered as HTML/CSS, not an SVG chart.
- **Chart D — SAME-R telemetry:** a phase/band and exception-position SVG plus a second SVG lag-autocorrelation plot. It visualizes archived products and labels them as not recomputed in deployment.
- An additional, unnumbered smoke-versus-dust particle-size panel is rendered as SVG. The plotted comparison is a static explanatory graphic, not a locally trained detector or a DAFT data product.

**Sources:** `frontend/app/ui/dashboard.tsx:834-851, 1216-1219`; `frontend/app/ui/charts.tsx:92-158, 271-307, 450-517, 517-688, 688-716`; `docs/demo.md:69-77`; `docs/architecture.md:30-41`.

### Reports, APIs, tests, and responsive behavior

- CSV and HTML reports are generated by `backend/src/reporting.py` and returned as attachments by `/reports/csv` and `/reports/html`. The CSV/HTML include ranked catalogue evidence, scenario context, citations/limitations, and summarized archived SAME-R metrics; they do not contain raw telemetry rows.
- Phase 2 adds read-only `/ml/datasets`, `/ml/tasks`, and `/ml/datasets/{dataset_id}/quality` endpoints with `/api` aliases. The registry reports local source provenance, DataCite state, schemas/units, exact row and missingness counts, labels/groups, and production-bundle availability.
- Automated tests cover the dataset registry against local files, all six task statuses, run-level class counts, grouped leakage checks, train-only preprocessing, causal features, and local-model status selection.
- Final `python -m pytest -q` results are listed in the Phase 2 status above; the suite includes the Phase 1 AI tests and Phase 2 registry/quality/split/feature tests.
- `frontend/app/globals.css` contains responsive breakpoints for the existing dashboard and the AI controls, chat, epistemic cards, and retrieval panel. TypeScript and production build passed during Phase 1; the Phase 2 reruns were attempted but could not start because this shell has no `npx`, `npm`, or available Node executable.

**Sources:** `backend/src/reporting.py:76-165`; `backend/app/main.py`; `backend/ai/router.py`; `tests/test_product.py`; `backend/tests/test_api.py`; `frontend/app/globals.css` (AI workspace rules and responsive breakpoints); `docs/validation.md:5-18`.

## 3. Partially Implemented Features

| Capability | What exists | Limitation |
|---|---|---|
| NASA PSI research catalogue | 14 Tier-1 records, DOI/source links, structured conditions, and 10 Tier-2 scope entries | Tier-1 rows are catalogue metadata, not imported raw measurement tables; PSI-22 has a pending DOI |
| SAME-R telemetry and lineage | Root scripts replay six selected runs and reconcile phase/cycle identities; deployed API validates a packaged archive | Deployed API does not replay raw rows or return measurement values; it returns classifications, summarized metrics, and exact row references |
| Dust/smoke discrimination | Catalogue-based interpretation and a static particle-size illustration | No DAFT raw measurements, labeled smoke-vs-dust training data, or validated detector classifier |
| Partial-gravity/fire simulator | Deterministic equations produce MOC, spread, index, and envelope plots | The MOC curve and lunar feature are code-defined hypotheses, not fitted measurements, a validated physical model, or a safety assessment |
| AI research assistant | Local Ollama HTTP client; allow-listed catalogue/archive/docs RAG corpus; deterministic TF-IDF retrieval; constrained prompts; 13 task modes; status/retrieve/chat/report/history routes; dashboard workspace | `/api/ai/status` detects `qwen3:4b`; generation itself remains host-dependent. Semantic truth cannot be guaranteed by prompt/sanitization, the index is in-memory, and optional embeddings/FAISS require explicit local configuration/install |
| Dataset discovery and preprocessing | Local PSI-101/catalogue registry, repeatable CSV loaders, RunID-grouped splitting, train-only missing-value handling/scaling, causal feature engineering, and read-only dataset/task/quality routes | The six-run archive labels are derived from band/phase rules; Task 6 is narrowly scoped and not independent fire/smoke ground truth |
| ML research workspace | Grouped Leave-One-RunID-Out evaluation, local model artifacts, inference/explainability APIs, and frontend | The narrow archive-label models are near chance; no useful prediction skill or independent fire/smoke classification claim is supported |
| Virtual spacecraft monitoring | Synthetic scenarios, bounded historical/user CSV replay, polling routes, anomaly alerts, and dashboard | No live sensor, flight alarm, confidence score, hardware, driver, or control path; source limitations remain visible |
| Scientific synthesis | Structured rules derive themes from catalogue records | It does not merge raw experimental data or model causal effects across investigations |
| Streamlit path | Legacy local app can replay local raw CSVs and export reports | It is separate from the deployed Next.js/FastAPI path and must not be described as the production processing route |

The raw PSI-101 CSVs are present locally, but the project documents do not establish redistribution terms. Their presence does not mean they are part of the backend bundle or permissible to redistribute. **Sources:** `backend/data/catalogue/investigations.json:3-35, 729-764`; `backend/app/archive.py:1-7, 44-112`; `backend/app/main.py:153-183`; `recover_phase_lineage.py:158-230`; `backend/src/catalogue.py:315-457, 467-514`; `docs/references.md:1-20`; `DECISIONS.md:23-31`.

## 4. Implementation Status (Against the Target 8-Phase Specification)

Repository inspection for the Phase 0 baseline found none of the following module directories. Phases 1–6 have since implemented their research workspaces and APIs; Phase 7 hardening and route-registration coverage are complete, subject to the external verification gates noted above:

| Requested module | Current status |
|---|---|
| Local Ollama AI Research Agent + RAG (`backend/ai/`) | **Phase 1 implemented.** Standard-library Ollama connection/status/chat/embed client, hardware-aware model recommendations, allow-listed corpus, deterministic local TF-IDF retrieval, optional embedding/FAISS path, citations, offline deterministic fallback, and frontend workspace. Online inference and optional dense retrieval remain to be verified on a host with Ollama/models installed. |
| Trained ML Fire Research Models (`backend/ml/`) | **Phase 3 implemented.** Grouped model evaluation, local artifacts, inference/explainability routes, and workspace; reported results are near chance and do not support useful predictive skill. |
| Virtual Spacecraft Monitoring (`backend/telemetry/`) | **Phase 4 implemented.** Synthetic/replay/upload polling, anomaly detection, and workspace. The Next proxy does not handle WebSocket upgrades; this is not a live sensor or hardware interface. |
| Fire Suppression & Mitigation Digital Twin (`backend/digital_twin/`) | **Phase 5 implemented.** Paired user-defined environmental boundary-condition trajectories only; it does not calculate flame response, MOC, heat transfer, extinction, or suppressant effectiveness. |
| Unified Scientific Decision-Support Workspace (`backend/decision_support/`) | **Phase 6 implemented.** Deterministically aggregates scenario inputs, server-ranked PSI catalogue relevance, retrieved RAG citations, and caller-supplied telemetry/ML/twin snapshots. It does not invoke an LLM or issue safety recommendations. |

The deployed application includes AI, ML, telemetry, digital-twin, and decision-support routes/workspaces. The Next proxy forwards HTTP requests; telemetry therefore uses polling rather than WebSockets. The digital twin is deliberately an uncalibrated boundary-condition interpolator, not a fire/suppression outcome model. Decision-support subsystem snapshots are caller-provided and not independently verified. **Sources:** `backend/app/main.py`; `backend/ai/`; `backend/ml/`; `backend/telemetry/`; `backend/digital_twin/`; `backend/decision_support/`; `frontend/app/ui/model.ts`; `frontend/app/ui/dashboard.tsx`; `frontend/app/ui/fire-suppression-digital-twin.tsx`; `frontend/app/ui/scientific-decision-support.tsx`; `frontend/app/api/backend/[...path]/route.ts`; `backend/pyproject.toml`; `backend/requirements.txt`; `requirements.txt`.

## 5. Available NASA Datasets, Formats & Provenance

### Catalogue provenance and Tier-2 scope

The two `investigations.json` files are byte-identical and each contains 14 Tier-1 records. Thirteen have DOI strings; twelve resolved to matching DataCite records in the Phase 2 check. PSI-20's DOI string returned HTTP 404, and PSI-22 / ACME E-FIELD remains “Pending PSI record DOI lookup.” The architecture document's “14 DOI-linked” wording is therefore inaccurate. The prompt-suggested PSI-101 DOI `10.60555/037m-9382` also returned HTTP 404; the locally catalogued and DataCite-verified DOI is `10.60555/2np7-jv14`.

| PSI ID | Investigation | DOI in local catalogue | DataCite status |
|---|---|---|
| PSI-101 | SAME-R | `10.60555/2np7-jv14` | Verified |
| PSI-102 | SAME | `10.60555/gd4k-8h62` | Verified |
| PSI-47 | DAFT / DAFT-2 | `10.60555/ztgj-d202` | Verified |
| PSI-26 | BASS | `10.60555/58h4-dy80` | Verified |
| PSI-25 | BASS-II | `10.60555/4qc4-de67` | Verified |
| PSI-98 | SAFFIRE-I | `10.60555/0t15-1z43` | Verified |
| PSI-99 | SAFFIRE-II/III | `10.60555/2chp-m469` | Verified |
| PSI-20 | ACME-BRE | `10.60555/vb93-3y72` | DataCite returned 404; not treated as verified |
| PSI-159 | ACME-CFI-G | `10.60555/cyt1-kh64` | Verified |
| PSI-22 | ACME E-FIELD | **Pending PSI record DOI lookup** | No DOI to check |
| PSI-69 | FLEX | `10.60555/mbq8-0451` | Verified |
| PSI-68 | FLEX-2/CFI | `10.60555/byp8-h018` | Verified |
| PSI-107 | SPICE | `10.60555/9kbh-e962` | Verified |
| PSI-106 | SLICE | `10.60555/pm12-rg61` | Verified |

Tier 2 consists of SOFIE; SAFFIRE-IV/V/VI; ACME CLD Flame; ACME s-Flame; FLEX-2J; FLEX-IT; FSDC; MIST; LSP; and CFE/ICF. These are scope-completeness records, not locally analyzed studies. The ~12.4 TB figure is repository scope, not local data volume. NASA PSI record metadata is described as CC0-1.0; the local PSI-101 files have no separate redistribution terms recorded.

**Sources:** `backend/data/catalogue/investigations.json:3-35, 729-764`; `backend/src/catalogue.py` (`REPOSITORY_SCOPE`); `README.md:12-25`; `docs/references.md:1-28`; NASA PSI `PSI-101` / DOI `10.60555/2np7-jv14`, and the other PSI IDs/DOIs listed above.

### Local PSI-101 Pyrell files

Seven direct `Run_NNN` directories contain raw CSVs (10,350 rows total) with the same 98-column header. The six-run archive selects Runs 63, 64, 76, 84, 95, and 97; Run 87 is locally present but not in `RUN_FILES` or the deployed six-run archive. Two CSVs under `data/raw/PSI-101/_quarantine/` have SHA-256 hashes identical to Runs 95 and 97; their “Run107” directory names are candidate labels, not independent experiments, and they are excluded from the raw-run count. Run_052 is represented by a PDF, Runs 071 and 074 by PPTX files, and `data/raw/PSI-101/Reports/Archived/SAMER_Final_0602_2014_archived.pdf` is a document rather than a row-level table.

| Run | File | Data rows | TestNumber counts | `-999` sentinel values |
|---:|---|---:|---|---|
| 63 | `Run_063/HKPData_gmt235_1.csv` | 1,236 | 63: 1,236 | `PTrakMeasurement(PtPerCC)`: 22; `ElapsedTestTime(Secs)`: 1 |
| 64 | `Run_064/HKPData_gmt235_3.csv` | 1,688 | 64: 1,626; 0: 62 | P-Trak: 6; elapsed: 1 |
| 76 | `Run_076/HKPData_gmt238_4.csv` | 1,427 | 76: 1,414; 0: 13 | P-Trak: 7; elapsed: 1 |
| 84 | `Run_084/HKPData_gmt242_1.csv` | 1,556 | 84: 1,498; 0: 58 | `CycleCounter`: 1; P-Trak: 376; elapsed: 1 |
| 87 | `Run_087/HKPData_gmt242_3.csv` | 751 | 87: 727; 0: 24 | P-Trak: 9 |
| 95 | `Run_095/HKPData_gmt250_4.csv` | 1,891 | 95: 1,826; 0: 65 | P-Trak: 197; elapsed: 1 |
| 97 | `Run_097/HKPData_gmt251_1.csv` | 1,801 | 97: 1,429; 0: 372 | `CycleCounter`: 1; elapsed: 1 |

The CSV profile found no empty cells in these seven files. It did find the `-999` sentinels above; they must be treated as missing/invalid per channel, not as physical measurements. The counts also show that a filename's run number is not sufficient row eligibility: several files contain `TestNumber=0` rows. The historical SAME-R filter uses the matching `TestNumber`, `RunMode=3`, `DustTrakAState=6`, and `DustTrakAPower=1` plus finite measurement/analog/cycle checks and other exclusion rules.

### Exact shared 98-column schema

Header from `data/raw/PSI-101/Pyrell/Run_063/HKPData_gmt235_1.csv`; the other six CSV headers were checked to match:

```text
TimeString, Time, RunMode, TestNumber, ElapsedTestTime(Secs), SampleNumber, CarouselNumber, DriveKBRemaining, CycleCounter, WatchdogReset, EnetSelect, EnetOverride, OKStatus, EventSet, EventCode, TestRunning, 12VDCHeaterEnable, HeatingInProgress, SampleHeaterOverride, GasPlumeTemperature(DegC), SampleResistance(Ohms), ISSDetectorObscurationMeasurement(Volts), ISSDetectorScatterMeasurement(Volts), STSDetectorMeasurement(Volts), IonDetectorAMeasurement(Volts), IonDetectorBMeasurement(Volts), PTrakMeasurement(PtPerCC), DustTrakAMeasurement(MgPerM3), DustTrakBMeasurement(MgPerM3), DustTrakAAnalogMeasurement(Volts), DustTrakBAnalogMeasurement(Volts), LFEFlowRate[AT08](SCCM), VSOSetpoint[PN23](Volts), ZeroLFE, MFCSetpoint(LPM), MFCMassFlowRate(LPM), MFCTemperature(DegC), MFCPressure(PSIA), MFCAnalogSetpoint[BN19](LPM), MFCAnalogFlowRate(LPM), GN2MainPressure[PN02](PSIA), GN2RegulatedPressure[PN12](PSIG), VacuumPressure[VR04](PSIA), DriveSidePressure[BN02](PSIA), SampleSidePressure[AT20](PSIA), ThermalPrecipitatorPreAgeChannel, ThermalPrecipitatorPostAgeChannel, PTrakState, PTrakKeySelect, PTrakPowerMeasurement(Volts), DustTrakAState, DustTrakAKeySelect, DustTrakBState, DustTrakBKeySelect, ProximitySensor1(Volts), ProximitySensor2(Volts), ProximitySensor4(Volts), CarouselProximitySensor(Volts), MixingFanPower, PTrakPower, DustTrakAPower, DustTrakBPower, STSDetectorPower, CarouselPower, PositionerEnable, PositionerDirectionIn, PositionerClock, GN2MainSolenoid[PN03], GateEnableSolenoid[PN07], InletGateSolenoid[BN08], OutletGateSolenoid[BN09], PistonControlSolenoid[BN17], DynamicDilutorSolenoid[PN15], PTrakSolenoid[VR06], CommDiagASolenoid[VR11], CommDiagBSolenoid[VR12], CommDiagADilutionSolenoid[PN24], CommDiagBDilutionSolenoid[PN27], PurgeSolenoid[VM09], PistonGN2Solenoid[BN18], PistonVentSolenoid[BN20], PistonVacuumSolenoid[BN16], ThermalPrecipitatorSolenoid[VM06], ThermalPrecipitatorPreAgeHeater, ThermalPrecipitatorPostAgeHeater, ThermalPrecipitatorPreAgeValve, ThermalPrecipitatorPostAgeValve, ThermalPrecipitatorPreAgeCableSense, ThermalPrecipitatorPostAgeCableSense, STSDetectorSelfTest, STSDetectorAlarmReset, STSDetectorAlarm, ISSDetectorSelfTest, VideoPower, VideoRecording, VideoPaused, CameraPower, IlluminationLEDPower
```

The unit-bearing sensor columns include DustTrak A/B mass (`MgPerM3`) and analog (`Volts`), P-Trak count (`PtPerCC`), gas plume/MFC temperature (`DegC`), sample resistance (`Ohms`), flow in `SCCM` or `LPM`, and pressure channels in `PSIA` or `PSIG`. The header does not supply a calibration certificate or a complete data dictionary; state, power, solenoid, and status columns are primarily discrete/control fields. The PDF and PPTX files were inventoried by format and size, not parsed for embedded tables or claims; their contents are not classified as absent.

**Sources:** CSV header row and data rows at `data/raw/PSI-101/Pyrell/Run_063/HKPData_gmt235_1.csv`, `Run_064/HKPData_gmt235_3.csv`, `Run_076/HKPData_gmt238_4.csv`, `Run_084/HKPData_gmt242_1.csv`, `Run_087/HKPData_gmt242_3.csv`, `Run_095/HKPData_gmt250_4.csv`, and `Run_097/HKPData_gmt251_1.csv`; `recover_phase_lineage.py:158-230`; `src/samer.py:32-107`; `docs/references.md:1-8`.

### Archived and derived metadata

`backend/data/metadata/` contains nine CSVs, which the deployed archive reads:

| File | Rows x columns |
|---|---:|
| `ArchivedExceptionCycleIDs.csv` | 297 x 3 |
| `MixedCycleIDs.csv` | 14 x 2 |
| `MixedCycleSourceRowRefs.csv` | 38 x 3 |
| `PSI101_Pyrell_DustTrakA_PhaseSummary_2026-11-14_170034.csv` | 12 x 16 |
| `PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_181648.csv` | 7,900 x 16 |
| `PSI101_Pyrell_DustTrakA_Periodicity_BlockEvents_20261114_181648.csv` | 101 x 11 |
| `PSI101_Pyrell_DustTrakA_Periodicity_LagCorrelation_20261114_181648.csv` | 240 x 4 |
| `PSI101_Pyrell_DustTrakA_Periodicity_CandidateModel_20261114_181648.csv` | 66 x 24 |
| `PSI101_Pyrell_DustTrakA_Periodicity_RunMetrics_20261114_181648.csv` | 6 x 34 |

The root `data/metadata/` contains 50 CSVs, five text audit reports, and `.gitkeep`. It includes a second periodicity snapshot (`20261114_183947`), phase-summary/exception and mixed-band products, cycle/row provenance audits, phase-lineage validation, and phase-reversal/episode-control analyses. The two periodicity snapshots each contain 7,900 cycle-sequence rows, 240 lag rows, 66 candidate-model rows, six run metrics, 101 block events, 80 boundary rows, and 51 excluded-cycle rows. The later phase-reversal snapshot (`20261114_183955`) contains 98 analog-comparison rows, 3,250 episode/control-metric rows, 7,900 timestamp-cycle rows, and 373 transition-aligned rows. The root `PhaseExceptions` product has 1,178 rows; the backend extract has 297 exception-cycle identities for the selected `RelativeCyclePhase` basis, not the full root product.

The bundled cycle-sequence schema is `RunID`, `Cycle`, `RelativeCyclePhase`, `ExpectedBand`, `ObservedBand`, `ExceptionIndicator`, `SourceRowCount`, `MixedBandIndicator`, `DuplicateCycleIndicator`, `DuplicateRowCount`, `SourceDataRows`, `FirstTimestamp`, `LastTimestamp`, `FirstTimestampSeconds`, `LastTimestampSeconds`, and `ClassifiedBandCount`. Its 7,900 cycles include 7,886 labeled rows (7,589 exception=0; 297 exception=1) and 14 mixed-band rows with blank exception labels. The six group IDs are 63, 64, 76, 84, 95, and 97. The 25 duplicate-cycle rows are flagged; these rows/labels are derived products, not independent outcome measurements.

The raw same-study record is locally available only for PSI-101. PSI-102/SAME, PSI-47/DAFT, BASS/BASS-II, SAFFIRE-I/II/III, ACME BRE/CFI-G/E-FIELD, FLEX/FLEX-2/CFI, SPICE, and SLICE are catalogue-only in this project; the local catalogue explicitly says their raw experiment files were not processed. No locally downloaded BASS-II, SAFFIRE, FLEX, ACME, SPICE, or SLICE measurement table was found. The audit found no physical sensor firmware, device driver, or hardware connection implementation; the telemetry CSVs and audit scripts are software-side historical data handling.

**Sources:** `backend/app/archive.py:13-35, 44-112`; `backend/data/metadata/` and `data/metadata/` CSV headers/data rows; `backend/data/catalogue/investigations.json:114, 194, 275, 357, 439, 520, 602, 684, 763, 848, 931, 1012, 1091`; `docs/references.md:5-20`; `docs/dataset_inspection_report.md:1-14`.

## 6. Existing Scientific Equations & Ranking Algorithms

The implementation contains two different classes of calculations: standard unit/scale calculations, and deterministic visualization/ranking heuristics. The latter must not be described as validated physical laws.

### Screening calculations

Let `g` be gravity in g, `V_forced` be selected airflow in cm/s, `P_psi` be total pressure in psi, and `O2_pct` be oxygen volume percent.

1. **Oxygen partial pressure:** `P_O2 = (O2_pct / 100) * P_psi`. The reference Earth-air value is `0.21 * 14.7 = 3.087 psi`. This is a unit/composition calculation, not a fire model.
2. **Buoyant velocity scale:** `V_b = 28.0 * sqrt(max(g, 0))` cm/s. The coefficient is a code-defined scale.
3. **Effective mixed convection:** `V_eff = sqrt(V_forced^2 + V_b^2)` (implemented using `hypot`).
4. **Fuel reference MOC:** substring rules assign 14% to selected liquid/droplet names, 16% to selected solid names, 12% to selected gas names, and 16% by default.
5. **MOC visualization surrogate:**

   `MOC = clamp(MOC_ref - 1.1*exp(-((g - 0.166)/0.18)^2) + 0.035*max(0, V_eff - 25) + 0.20*(3.087 - 0.21*P_psi), 5, 35)`

   The local term near 0.166 g is intentionally a shallow lunar feature, not a measured lunar result. `O2_pct` does not directly appear in this MOC equation; pressure does.
6. **Flame-spread visualization:** `lunar_boost = 1 + 0.35*exp(-((g - 0.166)/0.2)^2)` and `spread = max(0, (O2_pct - MOC)*0.16*lunar_boost / (1 + max(0, V_eff - 35)/45))`. This is not calibrated to a local flame-spread dataset.
7. **Flammability index:** the code clamps `50 + 2*max(0, O2_pct-MOC) + 18*(P_O2/3.087 - 1) - 0.7*max(0, V_eff-30)` to 0–100. It is explicitly a screening display, not a probability.
8. **E-FIELD display equivalence:** `V_equiv_kV = min(10, 10*sqrt(max(g,0)))`; `E_equiv = V_equiv_kV / 2.54 cm`. The code states no calibrated gravity-to-voltage conversion is asserted and requires E-FIELD matrices and measured ion-current/flow data before claiming equivalence.

The choice `V_b = 28*sqrt(g)` is a declared scaling; the `MOC`, flame-spread, lunar enhancement, index, and E-FIELD voltage mapping are code-defined surrogates. No local fitting or direct lunar measurement validates them. **Sources:** `backend/src/catalogue.py:9-20, 315-457`; `docs/methodology.md:35-70`; NASA PSI-25 (BASS-II), PSI-20 (ACME-BRE), and PSI-22 (ACME E-FIELD) are named as evidence anchors, not as proof that the formulas were fitted to their raw measurements.

### Ranking and synthesis

- `rank_studies()` evaluates research pillar, fuel/material string match, oxygen, pressure, airflow, and gravity. Known matches score 1, known disagreements score 0, and a documented apparatus capability (not a confirmed tested point) scores 0.5. Unknowns are omitted from the score denominator.
- `match_score = 100 * sum(known factor scores) / count(known factor scores)`; `evidence_coverage = 100 * scored applicable factors / applicable factors`. Factors are equally weighted, with no statistical calibration. The ranker sorts by score, coverage, then PSI ID.
- `_physics_proximity()` computes normalized range positions and a mean across known oxygen/pressure/airflow ranges; the implementation explicitly keeps this auxiliary number separate from the heuristic match score.
- `synthesize_scientific_insights()` builds structured themes and deltas from catalogue fields. It does not pool measurements across investigations.

These are deterministic research-relevance heuristics, not physical laws, risk scores, ignition probabilities, or trained models. **Sources:** `backend/src/catalogue.py:189-313, 467-514`; `backend/app/main.py:93-98, 109-123`; `docs/methodology.md:18-33, 114-122`.

## 7. Existing ML-Related Functionality

Phase 3 adds trained Logistic Regression, Random Forest, and Gradient Boosting classifiers for one narrow target: PSI-101 archived DustTrak-A `ObservedBand`. Input features are cycle-aligned DustTrak-B, P-Trak, gas plume temperature, sample resistance, and MFC flow; the DustTrak-A target-generating channels and archive label/phase fields are excluded. The 7,886 labeled rows are evaluated with six Leave-One-RunID-Out folds over Runs 63, 64, 76, 84, 95, and 97. The model artifacts are refit on all six runs for local inference; reported validation metrics are out-of-fold.

The measured results in `docs/PHASE3_MODEL_REPORT.md` are near chance (ROC-AUC 0.4967–0.4989; accuracy 0.4981–0.5010 versus a 0.5004 grouped-majority baseline). They do not establish useful predictive skill. This is not a fire, ignition, extinction, smoke-versus-dust, or nuisance-dust classifier. Confidence values are uncalibrated model scores; Brier/ECE are diagnostics, not calibrated intervals.

Training requires the optional scikit-learn dependency declared by `backend/pyproject.toml`; model serving uses versioned, non-executable JSON artifacts in `backend/ml/models/artifacts/` and does not load pickle/joblib files. Those artifacts are ignored by Git and kept local pending review of the rights for the contributing raw files and derived model. Exact empirical interventional Shapley values are enumerated by `backend/ml/explainability/explainer.py`, separately from native tree/coefficient importance; they describe model behavior, not physical causality. The Phase 1 Ollama client still generates explanations, not predictions.

The “CandidateModel” and “LagCorrelation” names refer to exploratory, deterministic SAME-R audit products:

- `recover_phase_lineage.py:92-126` grid-searches a square-wave pattern over periods 18–26, mismatch widths 8–13, and offsets. The binary “exception” label comes from the historic per-run phase/band mismatch rule. This is pattern fitting on a derived classification, not a trained fire model.
- The root `CandidateModel_20261114_183947.csv` has 66 rows: 54 `CandidatePeriod`, six `FullSequenceBest`, four `ChronologicalHoldout`, and two `ReportedWindowFit`. Full-sequence fits are explicitly in-sample; only runs 84 and 95 have within-run chronological split examples. In those rows the candidate often loses to the constant-majority baseline: Run 84 first-half-to-second-half accuracy 0.583 vs 0.712 baseline, and reverse accuracy 0.618 vs 0.995; Run 95 first-half-to-second-half 0.608 vs 0.854, and reverse 0.635 vs 1.000. These results do not demonstrate generalization to a held-out experimental run.
- The root lag file has 240 rows (40 lags x six archived runs). At lag 21, the archived autocorrelation is about 0.896 for Run 84 and 0.842 for Run 95; Run 97 has no valid lag pairs in the saved profile. Strong serial dependence makes random row-level train/test splits inappropriate.
- `phase_reversal_telemetry_audit.py` adds descriptive statistics, Hedges' g, and moving-block bootstrap intervals (1,000 resamples, block length 22). Statistical summaries and confidence intervals are not an ML training/inference pipeline.

The persisted backend archive remains the earlier `20261114_181648` product; the workspace contains later snapshots. Those audit products remain deterministic analyses, distinct from the Phase 3 estimators. **Sources:** `docs/methodology.md:1-3, 96-103`; `recover_phase_lineage.py:66-153, 158-246` (selection and cycle labels), `recover_phase_lineage.py:92-126, 330-418` (candidate fits and holdouts); `phase_reversal_telemetry_audit.py:20-21, 102-175`; `backend/app/archive.py:19-35`; `data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_CandidateModel_20261114_183947.csv`; `data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_LagCorrelation_20261114_183947.csv`; `backend/pyproject.toml` (optional ML extra).

Phase 3 verification: local registry and three JSON artifacts are present. Their recorded SHA-256 hashes match the archived cycle ledger and six selected raw-run CSVs; they were not regenerated for this release check. `/ml/models` and `/api/ml/models`, local dataset registry, all three explainability routes, unit-validated prediction, and the browser ML workspace returned successfully. The complete Python suite now reports 41 passing tests, and frontend typecheck/build pass using bundled Node.js 22.23.5/npm. Model artifacts remain Git-ignored pending raw-source and derived-model rights review; production artifact delivery is not configured.

## 8. Feasible Machine Learning Prediction Tasks (Grounded in Actual Local Data)

The Phase 2 registry evaluates the six requested candidate tasks against the actual inspected data. Task 5 is feasible for exploratory similarity/regime profiling; Task 6 is feasible for narrow archived-label classification and now has Phase 3 baseline model artifacts. Neither changes the status of Tasks 1–4, and Task 6 does not represent a validated fire/aerosol detection capability.

**Part 3 — Six Candidate ML Prediction Tasks (verbatim):**
1. Combustion outcome classification.
2. Flame extinction versus sustained combustion.
3. Ignition outcome classification.
4. Flame-spread or burning-rate regression.
5. Experimental condition similarity.
6. Smoke or aerosol experimental classification, if suitable labelled data exists.

| Candidate task | Phase 2 status | Evidence and limitations |
|---|---|---|
| 1. Combustion outcome classification | **NOT_TRAINABLE_FROM_LOCAL_RAW_DATA** | The local PSI-101 files are smoke-aerosol detector/instrument telemetry, not multi-material ignition/no-ignition outcomes across runs. Catalogue envelopes are not per-test targets. |
| 2. Flame extinction versus sustained combustion | **NOT_TRAINABLE_FROM_LOCAL_RAW_DATA** | BASS-II and FLEX extinction boundaries appear at catalogue-envelope level; no per-test raw extinction trial table is locally available. |
| 3. Ignition outcome classification | **NOT_TRAINABLE_FROM_LOCAL_RAW_DATA** | SAFFIRE and BRE are catalogue-level here; no local per-sample ignition outcome table was found. |
| 4. Flame-spread or burning-rate regression | **NOT_TRAINABLE_FROM_LOCAL_RAW_DATA** | The simulator spread value is a code-defined physics surrogate, not a measured training target; no local multi-material rate table was found. |
| 5. Experimental condition similarity | **FEASIBLE_EXPLORATORY** | Similarity/regime profiling may use the 14 Tier-1 catalogue envelopes and six archived PSI-101 run summaries. This is small-N descriptive exploration, not supervised prediction or validation across independent studies. |
| 6. Smoke or aerosol experimental classification, if suitable labelled data exists | **FEASIBLE_SUPERVISED_GROUPED_BY_RUN**, narrow scope only | The deployment-bundled cycle ledger has 7,900 records from six runs; 7,886 are non-mixed. `ObservedBand` has 3,946 `10000-14999` and 3,940 `20000+` labels; the separate phase-exception label has 7,589 class 0 and 297 class 1. Phase 3 trains only the former and does not claim fire, ignition, extinction, or smoke-versus-dust ground truth. Raw telemetry remains local-only. |

Task 6 requires all cycles from a physical burn to remain in one partition. The Phase 2 split utility checks disjoint RunID sets. Phase 3 uses leave-one-RunID-out evaluation over Runs 63, 64, 76, 84, 95, and 97. It joins those archive labels to local raw sensor rows using `SourceDataRows`, excludes mixed cycles, and excludes target-generating DustTrak-A signals plus archive label/phase fields from predictors. Despite this leakage control, the measured results are at chance and have no practical predictive value.

**Sources:** `backend/ml/datasets/registry.py` (`assess_candidate_tasks`); `backend/ml/preprocessing/pipeline.py` (`GroupedExperimentSplit`); `backend/ml/datasets/loader.py`; `backend/ml/training/trainer.py` (`build_training_dataset`, `train_models`); `backend/ml/evaluation/metrics.py`; `backend/ml/explainability/explainer.py`; `backend/data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_181648.csv`; raw CSV paths described in Section 5; `docs/PHASE2_DATASET_QUALITY_REPORT.md`; `docs/PHASE3_MODEL_REPORT.md`.

## 9. Backend Integration Points

The least disruptive integration seam is the existing FastAPI app in `backend/app/main.py`. The feature packages use independent `APIRouter`s under non-overlapping `/ai`, `/ml`, and `/api/...` paths, preserving current handlers:

| New package | Suggested router prefix/service boundary | Integration constraint |
|---|---|---|
| `backend/ai/` | **Implemented** at `/ai` with `/api/ai` aliases; retrieval, prompt, agent, and Ollama adapters are modular | Current corpus is an allow-list; exact source excerpts and citations are separate from generated explanation. Ollama offline returns a labeled deterministic RAG response. The live status endpoint detects `qwen3:4b`; generation itself remains unverified in this phase. |
| `backend/ml/` | **Phases 2–3 implemented** at `/ml` with `/api/ml` aliases for datasets, tasks, quality, model registry, inference, and explainability | Training is offline and requires local raw inputs; the API serves only generated JSON artifacts. Prediction applies only to archived band labels, validates units, reports grouped metrics, and disclaims calibration/operational use. |
| `backend/telemetry/` | **Phase 4 implemented** at `/telemetry` and `/api/telemetry`; scenario generator, local PSI-101/CSV replay, anomaly detector, and process-local polling state are modular | Uses HTTP polling because the existing proxy does not handle WebSocket upgrades. Synthetic and replay labels are explicit; unavailable PSI-101 channels remain null; thresholds are exploratory, not flight alarms. |
| `backend/digital_twin/` | `/digital-twin`; deterministic model/service boundary | Keep assumptions and units in schemas; do not present simulation outcomes as validated suppression recommendations. |
| `backend/decision_support/` | `/decision-support`; orchestration over typed evidence products | Aggregate links/statuses and uncertainty from existing services rather than duplicating catalogue or equations. |

Future modules should add router modules and tests, then mount them in `main.py`; they should not rename or change existing routes. The AI corpus/index is lazy and process-local; dense embedding setup is opt-in. ML model files are versioned safe JSON, but current generated artifacts are local-only and not available in a clean deployment until rights-reviewed model artifacts are provisioned. The packaged app serves read-only data and has no persistent database path. Vercel's current documentation lists WebSocket support as a **public beta**, but the repository's Next proxy does not forward WebSocket upgrades; this needs a dedicated integration decision, not an assumption that the current proxy will work.

**Sources:** `backend/app/main.py`; `backend/ai/router.py`; `backend/app/archive.py:1-7, 44-112`; `frontend/app/api/backend/[...path]/route.ts`; `vercel.json:1-24`; `docs/vercel-migration.md:17-33`; [Vercel Functions limits and WebSocket-related links](https://vercel.com/docs/functions/limitations).

## 10. Frontend Integration Points

The current UI is a single `Dashboard` component with a typed `TabId`, a central `TABS` list, state/effects, and conditional workspace rendering. Phases 1, 3, and 4 add focused AI, ML, and telemetry workspaces through those extension points rather than creating another dashboard:

1. The sixth typed tab and contracts are in `frontend/app/ui/model.ts`; `ai-research-assistant.tsx` is rendered by `dashboard.tsx` using shared catalogue/scenario/simulation/comparison state.
2. The AI workspace has its own request loading/errors, model/status, chat, history, and retrieval state; prior simulator, matrix, synthesis, SAME-R, executive, theme, and Developer modal behavior remains in the dashboard.
3. The seventh **ML · FIRE RESEARCH LAB** workspace is `ml-fire-research-lab.tsx`; it fetches the local model registry and explanations, displays grouped metrics/ROC/confusion matrix, and posts a unit-declared inference payload. The report labels the observed-band task and model scores as exploratory.
4. The eighth **VIRTUAL SPACECRAFT MONITORING** workspace is `virtual-spacecraft-monitoring.tsx`; it uses 1 Hz HTTP polling, labels synthetic/local/user-CSV sources, plots only present values, and displays rule-triggered alerts with their observations. The live chart leaves unrecorded PSI-101 O₂ and airflow channels blank.
5. Add future digital-twin and decision-support workspaces as focused components through the same tab mechanism; do not duplicate the dashboard.
6. If telemetry later needs WebSockets, add a separately supported proxy/deployment path; the current same-origin handler is not a WebSocket proxy.

The seven current workspaces share only the typed catalogue/scenario data they need, and the Executive View intentionally composes the original research workspaces. Keep future state local unless a typed shared contract is required. Existing responsive styles collapse the visualization grid and scale the mission heading; AI and ML workspaces use dedicated responsive styles. ML chart labels remain pure black/white by theme while plot colors remain distinct.

**Sources:** `frontend/app/ui/model.ts`; `frontend/app/ui/dashboard.tsx`; `frontend/app/ui/ai-research-assistant.tsx`; `frontend/app/ui/ml-fire-research-lab.tsx`; `frontend/app/ui/charts.tsx`; `frontend/app/globals.css`; `frontend/app/api/backend/[...path]/route.ts`.

## 11. Hardware, Memory & Performance Constraints

- **No hardware integration is required or present.** The current repository is software-only: historical instrument values are read from CSVs locally, but no sensor firmware, device driver, live hardware input, or physical telemetry controller was found.
- **Ollama memory:** the official Ollama library pages list Qwen3 4B at about 2.5 GB and Qwen3 8B at about 5.2 GB for the displayed Q4_K_M quantizations. Those figures are model blobs, not total runtime memory. KV cache/context length, parallel requests, embeddings, operating system, and CPU/GPU placement add overhead. The repository has no declared development-machine RAM/GPU inventory, so fit and latency must be benchmarked on the actual host. Prefer testing 4B first; do not promise 8B or long context without a measured memory/latency budget.
- **Embeddings/vector index:** base float32 vector storage is `document_count * dimensions * 4 bytes`, before index and metadata overhead. For scale, 10,000 768-dimensional vectors are about 29 MiB of raw float32 values; 100,000 are about 293 MiB. A FAISS/Chroma choice should follow a measured corpus and update/query test. Neither is currently a dependency. A local persistent index must not be assumed to survive a stateless/serverless instance or exist on a separate Vercel service.
- **WebSocket telemetry:** synthetic streams are computationally light if bounded and rate-limited; retaining unbounded history or broadcasting every raw row is not. The frontend proxy handles GET/POST/DELETE but does not proxy WebSockets. Vercel documents WebSocket support as a public beta, so access, service routing, connection lifetime, memory, and reconnect behavior need a deployment-specific test.
- **Vercel limits:** current Vercel documentation lists 2 GB maximum function memory on Hobby and 4 GB on Pro/Enterprise, 500 MB uncompressed Python bundle allowance (with larger-function options subject to separate availability), and duration limits that vary by plan. These are tight/uncertain targets for co-hosting Ollama model weights, an embedding model, and an index. Keep inference local or on a separately provisioned model host; do not package a multi-GB LLM into this Python function.
- **Current package footprint is deliberately small:** frontend runtime uses Next/React; backend runtime pins FastAPI; pytest/httpx/uvicorn are development dependencies. Adding Chroma, FAISS, transformers, or a model runtime changes install size, cold start, and deployment eligibility and requires explicit justification.

**Sources:** `backend/requirements.txt:1`; `backend/requirements-dev.txt:1-3`; `backend/pyproject.toml:1-8`; `docs/vercel-migration.md:1-33`; [Ollama Qwen3 4B](https://ollama.com/library/qwen3:4b); [Ollama Qwen3 8B](https://ollama.com/library/qwen3:8b); [Vercel Functions limits](https://vercel.com/docs/functions/limitations).

## 12. Scientific Limitations & Mandatory Epistemic Guardrails

The approved Phase 1 specification supplies the following exact mandatory principles.

**Part 9 — 14 Mandatory Scientific Reliability & Safety Principles (verbatim):**
1. Never fabricate NASA datasets.
2. Never invent experimental results.
3. Never claim an unvalidated model is scientifically accurate.
4. Clearly identify synthetic data.
5. Distinguish measured data from calculated values.
6. Preserve original dataset provenance.
7. Record units and measurement conditions.
8. Prevent training/test data leakage.
9. Report uncertainty.
10. Keep an audit trail.
11. Require human review for scientific interpretations.
12. Do not issue physical spacecraft control commands.
13. Do not operate fire-suppression equipment.
14. Do not represent the platform as NASA-approved or flight-certified.

The following operational checks translate those principles into repository-specific constraints:

1. **Preserve provenance:** every imported observation must retain PSI ID, file, run, row/time, and source URL/DOI where available.
2. **Separate evidence classes:** distinguish NASA PSI descriptions, local measured rows, archived derived products, code-defined physics surrogates, synthetic telemetry, ML outputs, and LLM text.
3. **Do not relabel a surrogate as measurement:** label current MOC, spread, flammability index, partial-gravity envelope, and E-FIELD scaling as unvalidated screening output.
4. **Do not relabel a prediction as fact:** every future ML result must identify target, training-data scope, model/version, validation protocol, uncertainty, and known out-of-domain limits.
5. **Treat LLM output as explanation only:** an answer is not a measurement, model prediction, source citation, engineering approval, or safety decision.
6. **Ground AI responses in retrieved evidence:** preserve exact source links and quoted passages; say “not found” when evidence is absent rather than filling gaps from model memory.
7. **Represent synthetic telemetry visibly:** include a persistent synthetic-data badge/field and never mix generated rows into NASA data views or training data without explicit labels.
8. **Keep units, calibration, and quality flags:** do not strip unit suffixes, interpret `-999` as a physical value, or silently combine incompatible measurement channels.
9. **Preserve unknowns:** do not impute unstated NASA metadata or treat an apparatus capability as a tested condition.
10. **Do not pool studies casually:** data from different investigations, instruments, fuels, and protocols require documented scientific harmonization before joint analysis.
11. **Prevent leakage:** split time-series evaluations by whole `RunID`/experiment and time; keep preprocessing, feature selection, and threshold selection inside training folds.
12. **Show uncertainty and class balance:** report per-run metrics, denominators, missingness, baseline, uncertainty, and limitations; do not hide zero-exception or imbalanced groups.
13. **Avoid operational claims:** no output should be labeled a fire prediction, safety score, certified suppression advice, design limit, flight rule, or approved atmosphere requirement without validated authority.
14. **Maintain attribution and non-endorsement:** cite NASA PSI/DOIs and individual data-file terms; state that the prototype is independent and not NASA-endorsed.

The current application already implements several of these boundaries: ranking is identified as research similarity rather than a safety score; archive responses explicitly say raw replay was not performed; the simulator marks `validated: false`; metadata license does not imply a license for raw files; and LUCI/FM2 data are not claimed. The Phase 1 system prompt includes the exact 14 principles; responses separate four epistemic tiers, expose retrieved citations, and filter unsupported PSI citation IDs, DOI strings, and numeric literals from local model prose. These controls are not a formal semantic verifier: human review and primary-source checks remain mandatory.

**Sources:** `README.md:475-507`; `docs/methodology.md:1-3, 29-33, 55-70, 84-122`; `docs/references.md:1-20`; `backend/app/main.py:72-75, 94-98, 118-123, 153-183`; `backend/src/catalogue.py:344-457`; `backend/app/archive.py:1-7, 109-112`.

## 13. Technical & Scientific Risks

| Risk | Evidence / likelihood | Impact | Mitigation and release gate |
|---|---|---|---|
| Ollama unavailable, stopped, or out of memory | Phase 1 client uses 2-second status and 45-second generation timeouts; inference requires a separately running local Ollama service | No live generation; a model may exceed host memory or time out | Expose offline/local status; deterministic retrieval remains available; use the 4B model first and benchmark on target hardware; surface non-connectivity errors. |
| RAG retrieval failure or uncited generation | Phase 1 uses a bounded approved corpus and tested lexical retrieval; ranking can still miss a relevant chunk | Evidence may be incomplete or an LLM may make a semantically unsupported claim | Keep exact source excerpts/citations visible, filter unknown citation IDs/DOIs and unsupported numeric literals, qualify empty retrieval, and require human source review. These are mitigations, not a proof of semantic correctness. |
| Small-sample overfit across runs | Six validated archive runs (seven raw CSVs visible); exceptions are concentrated in Runs 84/95 and absent in Run 97 | High apparent accuracy with poor run/study generalization | Split by `RunID`, preserve chronology, compare to simple baselines, report leave-one-run-out results and per-run uncertainty; do not claim model validity from rows alone. |
| Time-series autocorrelation leakage | Saved lags show high Run 84/95 correlation near lags 21/22; existing audit uses moving blocks | Random row split leaks neighboring cycles and inflates performance | Group by run and use blocked temporal evaluation; fit transforms/thresholds on train only; retain gaps and sentinel masks. |
| Weak-label or target leakage | SAME-R exception labels are calculated from measurement bands and phase mapping | A model can reproduce its label rule while being mistaken for fire detection | Document label derivation; exclude label-generating inputs; use independently annotated outcomes for any detector/fire target. |
| Raw data rights/provenance uncertainty | Project records do not establish PSI-101 raw-file redistribution terms | Inappropriate bundling or transfer of source files | Keep raw files local until per-file terms are verified; deploy only authorized derived/metadata products with provenance. |
| Vercel runtime mismatch for local models/state | Vercel function resource limits and the current stateless/read-only deployment pattern do not imply a persistent model host | Cold starts, memory exhaustion, unavailable Ollama endpoint, lost local index | Run Ollama/index on a separately provisioned host or research machine; use explicit service boundary and durable storage; benchmark package/cold-start budget. |
| WebSocket proxy mismatch | Current Next proxy exports GET/POST/DELETE only; Vercel WebSocket support is documented as beta | UI may never connect even if FastAPI WebSocket endpoint works locally | Treat streaming as its own integration task; test proxy/upgrade, auth, reconnect, timeouts, and production plan access before committing to this deployment path. |
| Synthetic/real data conflation | Synthetic and replay telemetry now exist as separate labeled sources | Demo traces may be mistaken for NASA measurements | Preserve source labels and provenance; do not mix generated rows into NASA data views or ML training without explicit labels. |
| Unvalidated digital-twin output | Phase 5 interpolates user-entered boundary conditions; local BASS-II/FLEX raw outcomes are unavailable and no fire-response model is calibrated | Users may interpret an environment trajectory as a suppression recommendation | Keep output limited to environment inputs, make missing flame response and unquantified uncertainty explicit, and require source-calibrated data plus independent validation before decision use. |
| Documentation drift | `DECISIONS.md`, `progress.md`, and several test/chart statements disagree with the current source | Misleading implementation or review assumptions | Update directly related docs in each approved phase; make tests and source the reference for current state. |

**Sources:** `data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_RunMetrics_20261114_183947.csv`; `data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_LagCorrelation_20261114_183947.csv`; `phase_reversal_telemetry_audit.py:20-21, 112-175`; `backend/app/archive.py:1-7, 109-112`; `frontend/app/api/backend/[...path]/route.ts:3-31`; `docs/vercel-migration.md:17-33`; [Vercel Functions limits](https://vercel.com/docs/functions/limitations).

## 14. Phase 1–Phase 7 Implementation Roadmap

Phases 1–7 local repository and proxy verification are complete. Frontend compilation passed using bundled Node.js 22.23.5/npm. Production ML remains an explicit release gate: the model artifacts are ignored by Git and there is no approved external artifact delivery binding. No production model availability claim is made.

| Phase | Objective and planned files | Dependencies | Acceptance criteria |
|---|---|---|---|
| **Phase 1 — Local Ollama AI Research Agent & Scientific RAG (complete)** | `backend/ai/{ollama,rag,retrieval,prompts,agents}`, `backend/ai/{schemas.py,router.py}`, `backend/app/main.py`, `frontend/app/ui/{model.ts,ai-research-assistant.tsx,dashboard.tsx,globals.css}`, the Next proxy, and backend tests. | Existing FastAPI/Pydantic and standard library. Optional Ollama embeddings/FAISS are opt-in; no paid API or new dependency. | **Met:** Offline retrieval, citations, history, and workspace integration are covered by tests. Live `/api/ai/status` detects `qwen3:4b`; live generation and optional dense retrieval remain unverified. |
| **Phase 2 — NASA Dataset Discovery, Ingestion & Quality Assessment (complete)** | Implemented `backend/ml/datasets/{registry.py,loader.py}`, `backend/ml/preprocessing/pipeline.py`, `backend/ml/features/engineering.py`, `backend/ml/router.py`, FastAPI mounting/tests, and `docs/PHASE2_DATASET_QUALITY_REPORT.md`. | Existing Python runtime only; no dependencies or external datasets added in Phase 2. Local raw data remains unbundled; file-level redistribution terms are not established. | **Met:** inventory/quality endpoints report local files, schemas, units, counts, missingness, labels/groups, provenance, DOI checks, and availability; six tasks are assessed; grouped split checks prevent RunID overlap; Phase 2 itself did not train models. |
| **Phase 3 — ML Model Development, Training, SHAP Explainability & ML Fire Research Lab (complete)** | Implemented `backend/ml/training/trainer.py`, `backend/ml/evaluation/metrics.py`, `backend/ml/explainability/explainer.py`, safe JSON inference in `backend/ml/models/`, model routes in `backend/ml/router.py`, frontend workspace/charts/types, and `docs/PHASE3_MODEL_REPORT.md`. | Optional `scikit-learn` extra for offline training; no SHAP dependency because exact empirical interventional Shapley values are enumerated directly. Model artifacts remain local due raw/derivative rights review. | **Met with negative scientific result:** three models evaluated on 7,886 labels using six Leave-One-RunID-Out folds; zero run overlap; metrics and calibration diagnostics recorded; all models are near chance and no useful prediction skill is supported; output is not labeled as fire/smoke. |
| **Phase 4 — Virtual Spacecraft Monitoring & Anomaly Detection (complete)** | Implemented `backend/telemetry/{simulator.py,ingestion.py,anomaly_detection.py,streaming.py}`, mounted router aliases in `backend/app/main.py`, and added `frontend/app/ui/virtual-spacecraft-monitoring.tsx`, synchronized SVG charts, typed telemetry contracts, styles, and `backend/tests/test_telemetry.py`. | Standard library + existing FastAPI only; bounded raw CSV-body upload avoids a multipart dependency. Uses HTTP polling, not WebSockets. Local PSI-101 replay requires raw files that are not in the deployment bundle. | **Met:** seven synthetic scenarios produce one-second timestamped JSON-safe frames; stream history is capped at 60; local replay preserves unavailable cabin O₂/pressure/airflow/gravity/smoke as null and keeps aerosol/instrument channels distinct; bounded CSV upload is labeled unverified; rule and rolling z-score alerts report triggers/observations without confidence scores; no hardware/control path. |
| **Phase 5 — Fire Suppression & Mitigation Digital Twin (complete)** | Implemented `backend/digital_twin/{schemas.py,simulator.py,router.py}`, mounted both API aliases, and added the `FIRE SUPPRESSION DIGITAL TWIN` workspace, typed response model, comparison chart, and scientific transparency panel. | Standard library + existing FastAPI/Pydantic. PSI-25 BASS-II, PSI-69 FLEX, and PSI-98 SAFFIRE-I are catalogue-context references only; numerical test tables are not locally available. | **Met within evidence limits:** strict input validation; paired 60-point environment trajectories; user-set targets and linear scenario ramps; explicit unquantified uncertainty; no inferred MOC/effectiveness/flame response; no physical control path; safety disclaimer and tests. |
| **Phase 6 — Scientific Decision Support Integration (complete)** | Implemented `backend/decision_support/{schemas.py,aggregator.py,synthesis.py,router.py}`, mounted both API aliases, and added the `SCIENTIFIC DECISION SUPPORT` dashboard with telemetry/ML/twin snapshot integration, catalogue ranking, RAG citations, epistemic sections, and Markdown export. | Reuses the existing catalogue ranking, screening calculation, and local RAG retriever. The synthesis itself is deterministic; it does not call an LLM to generate safety decisions or recommendations. | **Met:** validated scenario inputs; catalogue relevance and unvalidated MOC surrogate labeled; caller-provided telemetry/ML/twin results are explicitly unverified; RAG excerpts carry source references; missing integrations are surfaced; generated LLM suggestions remain empty; safety disclaimer and Markdown export included. |
| **Phase 7 — Testing, validation, documentation & deployment readiness (local verification complete)** | Updated backend missing-artifact diagnostics and tests, ML workspace unavailability explanation, Phase 3 report, README/progress/audit, and the Windows launcher. | Python 3.12–3.15 and Node.js 22.x. Production inference additionally requires authorized model artifacts and a configured delivery mechanism. | **Met locally:** 41 Python tests pass; frontend typecheck/build pass with bundled Node.js 22.23.5/npm; feature routers and aliases register; local FastAPI and Next proxy return expected responses; actual local ML registry, explanations, and prediction workflow render. **Pending:** verify a deployed backend artifact-loading mechanism after rights review; do not claim production ML availability until then. |

**Roadmap basis:** current route and UI seams in `backend/app/main.py`, `backend/ai/router.py`, `backend/ml/router.py`, `backend/telemetry/streaming.py`, `backend/digital_twin/router.py`, `backend/digital_twin/simulator.py`, `backend/decision_support/router.py`, `backend/decision_support/aggregator.py`, `backend/decision_support/synthesis.py`, `frontend/app/ui/model.ts`, `frontend/app/ui/ai-research-assistant.tsx`, `frontend/app/ui/ml-fire-research-lab.tsx`, `frontend/app/ui/virtual-spacecraft-monitoring.tsx`, `frontend/app/ui/fire-suppression-digital-twin.tsx`, `frontend/app/ui/scientific-decision-support.tsx`, `frontend/app/ui/charts.tsx`, and `frontend/app/ui/dashboard.tsx`; current dependency and deployment boundaries in `backend/pyproject.toml`, `backend/requirements.txt`, `frontend/package.json`, `vercel.json`, and `docs/vercel-migration.md`.
