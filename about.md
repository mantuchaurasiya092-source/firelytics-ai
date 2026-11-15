# FIRELYTICS AI - Team Onboarding & Architecture Guide

This guide introduces the research problem, current application architecture, workspace behavior, code ownership, and demo boundaries. It is written for Chandan Kumar Sah, Saurav Shah Teli, Mantu Kumar Chaurasiya, Bhola Sah, Digambar Updahaya, and Aakash. It documents the repository as implemented; it does not assign new commitments or claim unverified scientific results.

## 1. What FIRELYTICS AI is and the problem it explores

FIRELYTICS AI is an independent research dashboard for navigating NASA Physical Sciences Informatics (PSI) combustion-investigation metadata and selected reconciled outputs from archived PSI-101 SAME-R analysis. It helps a team compare what experiments document, examine how a hypothetical scenario relates to those records, and see where evidence is absent. It is not a fire detector, validated flammability model, spacecraft design tool, or NASA product.

Gravity changes how buoyancy transports heat and combustion products. At **0g**, buoyancy-driven flow is greatly reduced; diffusion, radiation, oxygen transport, and imposed ventilation have greater influence. **Lunar gravity (0.166g)** and **Mars gravity (0.376g)** are partial-gravity regimes where behavior cannot be inferred as a directly measured midpoint from the data available here. **Earth gravity (1g)** provides a normal-gravity screening reference. Real behavior also depends on fuel, geometry, oxygen, pressure, radiative losses, and imposed flow.

One dashboard question uses **34% O- at 10.2 psi** as a hypothetical lunar-habitat screening input. It is not an approved habitat specification. For that case, the oxygen partial pressure is 3.468 psi. The scenario asks how available evidence and the code's transparent screening surrogate behave under those inputs; it does not establish a safe limit or predict a fire.

NASA PSI repository-wide scope is represented as **24 combustion investigations and approximately 12.4 TB**. That number is repository context, not the amount downloaded or analyzed by this project. The catalogue deeply indexes 14 investigations and lists 10 related studies as scope context. The project analyzes selected archived PSI-101 Pyrell outputs for six runs; packaged service outputs are reconciled archive products, not a fresh replay of original raw files. Raw-file presence does not establish redistribution permission.

## 2. System architecture and technology

### Request path

1. The browser loads the Next.js application at `frontend/app/page.tsx`; the page mounts the dashboard in `frontend/app/ui/dashboard.tsx`.
2. Workspace components use typed contracts from `frontend/app/ui/model.ts` and render the charts and panels in `frontend/app/ui/charts.tsx` and their own component files.
3. Browser requests use the same-origin route `/api/backend/[...path]`, implemented in `frontend/app/api/backend/[...path]/route.ts`. The route validates path segments, forwards supported GET, POST, and DELETE requests to `BACKEND_URL`, and carries response status and selected headers back to the browser.
4. FastAPI starts from `backend/app/main.py`, mounts modular routers, and reads the catalogue, archive references, model registry, and other service data.
5. The response returns through the proxy; the UI checks status and payloads, then presents results with evidence provenance and scope notes.

### Stack and modules

- **Frontend:** Next.js 16 App Router, React 19, TypeScript, native SVG, and CSS. The dashboard is a client-side interactive workspace; the production build statically renders the root shell and exposes the dynamic API proxy route.
- **Backend:** Python 3.12-3.15 and FastAPI. The API is split into domain modules:
  - `backend/src/catalogue.py` - catalogue loading, evidence ranking, scenario screening calculations, and structured synthesis.
  - `backend/app/archive.py` - validates and serves the packaged SAME-R summaries, cycle sequences, exceptions, mixed-band identities, and references.
  - `backend/src/reporting.py` - deterministic CSV and HTML report generation.
  - `backend/ai/` - research request schemas and routes, prompt/agent orchestration, local Ollama client, RAG corpus indexing, chunking, and retrieval.
  - `backend/ml/` - dataset registry and quality audits, feature preparation, grouped model evaluation, inference, metrics, and explainability.
  - `backend/telemetry/` - input ingestion, replay/synthetic streaming, and rule-based anomaly analysis.
  - `backend/digital_twin/` - the fire-suppression scenario simulator and schemas.
  - `backend/decision_support/` - deterministic synthesis of scenario and supporting telemetry/model/evidence snapshots.
- **Deployment:** `vercel.json` describes separate frontend and backend services. The frontend requires `BACKEND_URL`; AI text generation also requires a reachable Ollama endpoint and available model. Retrieval and citations can operate without text generation.

## 3. The ten workspaces

The dashboard exposes these ten areas. Feature availability depends on the backend and the relevant data/configuration being present.

1. **Mission & Habitat Simulator** - selects a habitat or custom oxygen, pressure, flow, material, and gravity scenario; ranks catalogue evidence and plots code-defined screening outputs.
2. **Catalogue & Comparison Matrix** - searches investigation metadata, opens source records, and compares two to four selected PSI investigations. It compares documented catalogue fields, not raw measurement tables.
3. **SI Fire-Safety Synthesis** - combines deterministic evidence ranking, documented factors, limitations, and report downloads. Match score, evidence coverage, and physics proximity remain distinct quantities.
4. **PSI-101 SAME-R Telemetry & Lineage Lab** - reviews the archived six-run outputs, phase classifications, exceptions, mixed rows, missing/duplicate cycles, periodicity summaries, and source-row references.
5. **All-in-One Executive View** - provides a consolidated view of scenario outputs, ranked evidence, archived SAME-R status, and key scientific limitations.
6. **AI Scientific Research Assistant** - offers bounded research tasks, status/model selection, cited retrieval, chat history, and structured reports/proposals. Ollama is an optional generation engine; the route and payload retain engine-specific internal fields.
7. **ML Fire Research Lab** - shows the archived registry, run-held-out metrics, confusion/ROC diagnostics, Shapley summaries, and an exploratory score form. The target is a binned archived DustTrak-A observed band, not fire/ignition/extinction or smoke-versus-dust classification.
8. **Virtual Spacecraft Monitoring** - streams synthetic or selected historical channels, displays rule-based anomaly messages, and distinguishes source modes. It is a software demonstration, not a flight alarm.
9. **Fire Suppression Digital Twin** - compares deterministic simulated baseline and intervention trajectories. Results are modeling scenarios, not validated suppression-performance claims.
10. **Scientific Decision Support** - combines an active scenario with catalogue context, retrieved citations, and supplied subsystem snapshots into an evidence-linked brief. It does not make operational safety decisions.

### Charts A-D: four visualization families

The chart family labels below describe the main scientific visuals. Charts A, B, and D use native browser SVG; Chart C's evidence-factor tracks use HTML/CSS. Other workspace components also include native SVG plots for model diagnostics and telemetry.

- **Chart A - Oxygen/pressure flammability envelope:** shows screening boundaries, regime regions, habitat markers, and an active scenario in O2/pressure space.
- **Chart B - Partial-gravity/E-FIELD bounding curve:** compares surrogate values across gravity nodes and gives an explicitly illustrative PSI-22 E-FIELD analogy.
- **Chart C - Ranked evidence factors:** shows per-factor catalogue matches, mismatches, and unknowns. It is an HTML/CSS visualization, not an SVG chart.
- **Chart D - SAME-R phase agreement and aerosol-size context:** summarizes archived phase-band agreement and the catalogue-level SAME-R/DAFT discrimination context; it does not establish a deployed detector threshold.

### Evidence boundaries and modeling notes

The API marks the screening model `validated: false`. Its reported MOC, flame-spread, flammability-index, envelope, and partial-gravity values are code-defined visualization surrogates. Under the representative lunar inputs recorded in the README (34% O-, 10.2 psi, 14 cm/s, and the named example fuel), the reported MOC outputs are **15.72% at 0g**, **15.09% at 0.166g**, and **16.41% at 1g**. These exact values are reproducible outputs of the current heuristic, not measurements, validated limits, predictions, or safety decisions.

The proposed partial-gravity curve is bounded using 0g evidence, 1g screening, and a PSI-22 E-FIELD ion-driven analogy. E-FIELD voltage scaling is illustrative, not a calibrated gravity conversion. Direct LUCI/FM2 lunar-gravity measurements are not included. The full 14 Scientific Safety Principles and their implementation audit are preserved in [`docs/ADVANCED_IMPLEMENTATION_AUDIT.md`](docs/ADVANCED_IMPLEMENTATION_AUDIT.md).

The research assistant indexes approved catalogue/project metadata, packaged archive summaries, and named methodology/reference documents; it retrieves citations and may ask the configured model to draft a response. A generated response is not source evidence. Review its citations and separate NASA record metadata, project calculations, hypotheses, and suggestions. Text generation can be unavailable while deterministic retrieval remains available.

The ML pipeline uses experiment/run identity as the grouping boundary. The PSI-101 `RunID` is inferred from its source `Run_NNN` directory because the raw CSV rows do not carry a `RunID` column. LeaveOneGroupOut or GroupKFold must hold out an entire run; splitting cycles randomly could leak run-specific signatures into both training and evaluation. The archived model registry reports grouped evaluation over six runs and characterizes results as exploratory; the separate four/one/one group split is a small holdout, not a large independent validation study. Do not describe these classifiers as fire prediction.

## 4. Codebase map

### Root files

| Path | Purpose |
|---|---|
| `README.md` | Project overview, scope, scientific notes, API reference, and demo guidance. |
| `about.md` | This onboarding and architecture guide. |
| `start-firelytics.bat` | Windows launcher entry point; delegates to the PowerShell launcher. |
| `start-local.ps1` | Creates/updates the Python environment, checks frontend dependencies, starts local services, checks health/proxy, and opens the configured browser. |
| `vercel.json` | Frontend/backend deployment service and routing configuration. |
| `DECISIONS.md`, `progress.md` | Project decisions and historical progress notes. |
| `requirements.txt` | Root product-test dependencies. |
| `phase_reversal_telemetry_audit.py`, `recover_phase_lineage.py` | Archive audit and lineage recovery utilities; inspect their arguments before running. |

### Frontend

| Path | Responsibility |
|---|---|
| `frontend/app/page.tsx` | Root page entry. |
| `frontend/app/layout.tsx` | Document shell and page metadata. |
| `frontend/app/globals.css` | Shared layout, theme, panels, forms, and chart styles. |
| `frontend/app/api/backend/[...path]/route.ts` | Same-origin API proxy to `BACKEND_URL`. |
| `frontend/app/ui/dashboard.tsx` | Dashboard navigation, data loading, executive view, catalogue, and shared composition. |
| `frontend/app/ui/model.ts` | TypeScript request/response types and frontend domain types. |
| `frontend/app/ui/charts.tsx` | Shared SVG chart and visualization components. |
| `frontend/app/ui/ai-research-assistant.tsx` | AI status, retrieval, chat, citations, and reports. |
| `frontend/app/ui/ml-fire-research-lab.tsx` | Model registry, diagnostics, explainability, and exploratory prediction UI. |
| `frontend/app/ui/virtual-spacecraft-monitoring.tsx` | Telemetry source controls, stream display, and alert UI. |
| `frontend/app/ui/fire-suppression-digital-twin.tsx` | Digital-twin controls and trajectory UI. |
| `frontend/app/ui/scientific-decision-support.tsx` | Synthesis request, evidence brief, and Markdown export. |
| `frontend/package.json`, `package-lock.json` | Scripts, pinned dependencies, and reproducible frontend install. |
| `frontend/scripts/next.mjs`, `next.config.ts`, `tsconfig.json` | Next.js process wrapper and configuration. |
| `frontend/public/assets/` | Logo and laboratory/space background assets. |

### Backend, data, and tests

| Path | Responsibility |
|---|---|
| `backend/app/main.py` | FastAPI app, core catalogue/scenario/archive/report routes, and router mounting. |
| `backend/app/archive.py` | SAME-R archive file loading and consistency checks. |
| `backend/src/catalogue.py`, `backend/src/reporting.py` | Catalogue/scoring/surrogate implementation and deterministic exports. |
| `backend/ai/router.py`, `schemas.py`, `agents/`, `ollama/`, `rag/`, `retrieval/`, `prompts/` | AI endpoints, validation, orchestration, model client, indexing, retrieval, and prompts. |
| `backend/ml/router.py`, `datasets/`, `features/`, `preprocessing/`, `training/`, `evaluation/`, `explainability/`, `models/` | ML APIs, source/quality registry, features, training, evaluation, explanation, and inference artifacts. |
| `backend/telemetry/ingestion.py`, `streaming.py`, `simulator.py`, `anomaly_detection.py` | Telemetry inputs, modes, streams, and rule-based anomaly detection. |
| `backend/digital_twin/` | Digital-twin API schemas, route, and simulator. |
| `backend/decision_support/` | Synthesis route, aggregation, schema, and output construction. |
| `backend/data/catalogue/investigations.json` | Packaged 14-record catalogue. `data/catalogue/investigations.json` is its root-level counterpart. |
| `backend/data/metadata/` | Packaged archive summaries, cycle sequence, exception and mixed-row identities, and metrics for six runs. |
| `data/metadata/` | Research provenance and inspection files. |
| `data/raw/PSI-101/` | Optional source subset in the developer workspace; ignored by Git and not packaged into the deployed archive service. |
| `backend/tests/test_api.py`, `backend/tests/test_telemetry.py` | Backend route, data/ML, archive, and telemetry tests. |
| `tests/test_product.py` | Root product, source, and provenance checks. |
| `docs/architecture.md`, `methodology.md`, `references.md`, `validation.md`, `demo.md` | Architecture, formulas, citations, checks, and demo script. |
| `docs/ADVANCED_IMPLEMENTATION_AUDIT.md`, dataset inspection reports | Detailed safety principles, implementation review, and dataset constraints. |

## 5. Team roles, file ownership, and judge Q&A

The names and roles below follow the in-app Developer modal. These are collaboration guides based on the listed responsibilities, not access-control rules. Coordinate changes through review and keep API contracts, provenance, and scientific caveats intact.

### Chandan Kumar Sah - Project Lead & Backend Engineer

**Focus:** technical direction, API contracts, service integration, and backend architecture. Key areas: `backend/app/`, `backend/src/`, `backend/ai/`, `backend/ml/`, `backend/telemetry/`, `backend/digital_twin/`, `backend/decision_support/`, and `vercel.json`.

**Judge question:** How do you prevent the dashboard from claiming more than the evidence supports? Answer: catalogue match and coverage are explicit, unknowns remain unknown, archive responses distinguish archived products from raw replay, and screening outputs carry `validated: false` and limitations. None is an operational safety determination.

### Saurav Shah Teli - Frontend & Dashboard Visualization

**Focus:** Next.js dashboard, reusable UI, responsive layout, charts, and frontend/API integration. Key areas: `frontend/app/ui/`, `frontend/app/api/backend/`, `frontend/app/globals.css`, and `frontend/public/assets/`.

**Judge question:** Are the curves measured NASA data? Answer: the charts may show catalogue-linked evidence context, but the calculated envelope and partial-gravity curve are deterministic project screening surrogates. The API labels the model `validated: false`; the visuals do not turn a surrogate into a measurement.

### Mantu Kumar Chaurasiya - Data Engineering & Dataset Curation

**Focus:** source organization, metadata, lineage, preprocessing, and analysis-ready data. Key areas: `data/`, `backend/data/`, `backend/ml/datasets/`, `backend/ml/features/`, `backend/ml/preprocessing/`, and the archive/provenance documentation.

**Judge question:** Does 12.4 TB mean this app processed all NASA PSI files? Answer: no. It is the repository-wide scope figure for 24 investigations. The app deeply indexes 14 metadata records, gives 10 associated studies scope context, and serves reconciled products for six selected PSI-101 runs. It does not bundle the full repository or original source measurements.

### Bhola Sah - Quality Assurance & Testing

**Focus:** test coverage, API behavior, scientific-data integrity, and regression checks. Key areas: `backend/tests/`, `tests/test_product.py`, and `docs/validation.md`.

**Judge question:** How do you check the archived lineage? Answer: tests and archive validation compare the packaged phase summaries and cycle sequences with exact exception/mixed-cycle identities, duplicate and missing cycle counts, and source-row references. The online service reports references and archive reconciliation; it does not claim a new raw-data replay.

### Digambar Updahaya - Scientific Research & Documentation

**Focus:** combustion literature, NASA investigation context, evidence interpretation, methods, and citations. Key areas: `docs/methodology.md`, `docs/references.md`, `docs/ADVANCED_IMPLEMENTATION_AUDIT.md`, and README scientific sections. Profile links: **-**.

**Judge question:** What do you know about lunar-gravity flammability from this build? Answer: no direct LUCI/FM2 lunar-gravity measurements are included. The displayed lunar curve is a hypothesis bounded by available 0g and 1g context and an illustrative PSI-22 E-FIELD analogy; it needs direct measurements to test it.

### Aakash - Team Member (Profile pending)

**Focus:** the in-app modal lists deployment/platform configuration, environment integration, build/release workflow, runtime monitoring, logs, and health checks. Likely touchpoints are `start-firelytics.bat`, `start-local.ps1`, `frontend/package.json`, `backend/pyproject.toml`, `vercel.json`, and deployment docs. Profile: **Profile pending**.

**Judge question:** What must be configured for deployment? Answer: deploy the FastAPI and Next.js services and provide the frontend's `BACKEND_URL` binding. AI generation additionally requires a reachable Ollama endpoint and a model. The backend packages reconciled archive products, not ignored raw PSI-101 input files.

## 6. Quick verification and demo launch

From a Windows PowerShell terminal opened at the repository root:

```powershell
.\start-firelytics.bat
```

The launcher checks Python 3.12-3.15 and Node.js 22, creates or updates `.venv-local`, installs dependencies when its lock/requirements hashes change, checks backend and frontend health, launches services, verifies `/api/backend/health`, and opens the frontend. Visit `http://localhost:3000`; the backend API documentation is at `http://127.0.0.1:8000/docs`. The launcher runs the development frontend. For a judge demo, rehearse the scenario from [`docs/demo.md`](docs/demo.md) and leave time for the first service startup.

To run the complete Python suite from the repository root:

```bash
python -m pytest -q
```

The expected suite count in this repository is **40 tests**. It has passed 40/40 in the recorded verification. Some raw-replay/provenance checks depend on the optional ignored raw source subset; a clean clone may not contain those files. The deployed backend tests and archive features use packaged reconciled outputs. Frontend checks are `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` with Node.js 22 and dependencies installed.

## 7. Short demo narrative

1. Start with the scope distinction: 24 investigations/about 12.4 TB of repository scope, 14 deeply indexed records, 10 associated studies, and six archived PSI-101 runs. Do not imply the whole repository was downloaded.
2. Enter or select the 34% O- / 10.2 psi lunar screening scenario. State that this is a hypothetical input and not a habitat standard.
3. Show the catalogue factors and unknowns; explain that evidence similarity is not a risk score.
4. Show Chart B and the surrogate output table. Call the curve a hypothesis and point to its 0g/1g anchors and PSI-22 analogy.
5. Open the SAME-R workspace to explain archive validation and row references. Say explicitly that the service does not replay or expose original source measurements.
6. If AI/ML/telemetry features are shown, identify model generation as optional, classifier output as exploratory, and telemetry alarms as software rules-not operational decisions.

## 8. Non-negotiable science and data-use boundaries

- Repository size is scope context, not project processing volume.
- The 34% O- / 10.2 psi profile is a screening scenario, not an approved lunar habitat atmosphere.
- Surrogate values are not measurements, validated limits, predictions, or safety determinations.
- The 14 Scientific Safety Principles in the advanced implementation audit remain the detailed reliability baseline.
- No LUCI/FM2 direct lunar-gravity measurements are claimed; PSI-22 is an analogy, not a calibrated gravity substitute.
- LeaveOneGroupOut/GroupKFold must keep each `RunID` out of both training and validation at once. Cycle-level random splits invite experiment/run leakage.
- The classification target is the archived DustTrak-A observed band, not fire occurrence, ignition, extinction, or smoke-vs-dust identity.
- AI-generated wording is not evidence; review sources and citations.
- DataCite/metadata licensing does not automatically grant redistribution rights for every raw file. Check source-specific terms.
- FIRELYTICS AI is not endorsed by NASA and is not an operational tool.
