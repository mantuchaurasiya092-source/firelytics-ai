# FIRELYTICS AI — Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data

*A Physics-Informed Scientific Intelligence (SI) Workbench & NASA Physical Science Informatics (PSI) Decision Platform for Crewed Space Exploration and Terrestrial Fire Safety.*

[![NASA Space Apps Challenge](https://img.shields.io/badge/NASA-Space%20Apps%20Challenge-111111?style=flat-square)](https://www.spaceappschallenge.org/)
[![Stack](https://img.shields.io/badge/Next.js%2016-React%2019%20%7C%20TypeScript-111111?style=flat-square)](https://nextjs.org/)
[![API](https://img.shields.io/badge/API-Python%20%7C%20FastAPI-111111?style=flat-square)](https://fastapi.tiangolo.com/)
[![PSI scope](https://img.shields.io/badge/NASA%20PSI-24%20studies%20%7C%20~12.4%20TB-111111?style=flat-square)](https://psi.nasa.gov/)
[![Catalogue](https://img.shields.io/badge/Deeply%20indexed-14%20%7C%2013%20DOI--linked-111111?style=flat-square)](#full-nasa-psi-repository-coverage-24-investigations-124-tb-scope)
[![Tests](https://img.shields.io/badge/Automated%20tests-41%2F41%20passing-111111?style=flat-square)](#automated-verification-testing--scientific-guardrails)

> **Scope note:** NASA PSI's ~12.4 TB figure describes repository-wide scope; it is not the amount of data downloaded or processed by this project. Fourteen records are deeply indexed; thirteen have DOI links and PSI-22 (ACME E-FIELD) has a NASA PSI record whose DOI is pending.
>
> **Core project pillars:** **24 NASA PSI investigations / ~12.4 TB repository scope** and **14 Scientific Safety Principles**. Only 14 records are deeply indexed; see the [scope accounting](#full-nasa-psi-repository-coverage-24-investigations-124-tb-scope) and [full safety-principles audit](docs/ADVANCED_IMPLEMENTATION_AUDIT.md#12-scientific-limitations--mandatory-epistemic-guardrails).

## 1. Hero Header & Mission Badges

FIRELYTICS AI turns NASA Physical Science Informatics (PSI) combustion-research metadata and a reconciled subset of archived SAME-R analysis into a traceable workbench for exploring fire-safety evidence. It is an independent research and educational prototype, not a NASA operational tool.

| At a glance | Implementation |
|---|---|
| Challenge | NASA Space Apps Challenge — *Flame in Freefall* |
| Web application | Next.js 16.4.6, React 19.3.1, TypeScript |
| Scientific API | Python 3.12–3.15, FastAPI 0.117.1 |
| Repository scope | 24 NASA PSI combustion investigations; ~12.4 TB of repository scope |
| Indexed catalogue | 14 investigations; 13 DOI-linked records and one DOI pending |
| Automated suite | 41 Python tests across root product/provenance checks and backend API tests |

The “SI” workbench uses deterministic ranking and transparent screening logic. Its optional research assistant connects only to a separately hosted local Ollama service; it does not call a paid external generative-AI or NASA model service.

## 2. Executive Summary & The Challenge Context

On Earth, buoyancy shapes many flames and carries heat and smoke upward. In microgravity, that buoyancy-driven plume is greatly reduced: oxygen transport, diffusion, radiation, and imposed ventilation become more influential. Many quiescent flames can appear more rounded than the familiar buoyant teardrop, but flame shape and burning behavior still depend on fuel, geometry, radiation, and residual or forced flow.

The operational motivation is consequential:

- **Apollo 1 (1967):** the ground-test cabin's 100% oxygen at 16.7 psi contributed to the fatal pre-launch fire.
- **Apollo 13 (1970):** an oxygen-tank failure and associated spacecraft damage illustrate the severity of oxygen-system hazards; this was not a cabin-flame experiment.
- **Mir (1997):** a Vika/TGK solid-fuel oxygen generator caught fire aboard the station.
- **Artemis II:** the catalogue uses smoke-alarm nuisance/false-alarm concerns as mission-readiness context. This repository does **not** contain verified Artemis II in-flight smoke telemetry or support an “80,000 miles from Earth” alarm event; it should not be presented as an observed incident.

### The lunar-atmosphere screening question

The dashboard includes a hypothetical lunar-habitat screening profile of **34% O2 at 10.2 psi** and an EVA suit screening profile of **100% O2 at 4.3 psi**. The first is a scenario input, not an approved Artemis habitat or pressurized-rover atmosphere. At 34% O2, the oxygen mole fraction is about 62% above the 21% Earth-air reference, while the profile's O2 partial pressure is 3.468 psi (versus 3.087 psi for the code's sea-level reference). The catalogue separately records ACME-BRE cases at **26.5% O2 / 10.2 psia** and **34% O2 / 8.2 psia**; those experiments are not the same as the dashboard's 34% / 10.2 psi scenario.

FIRELYTICS organizes evidence around five questions: **Prevention**, **Detection**, **Suppression**, **Partial-Gravity Bounding**, and **Earth Spin-offs**. Its purpose is to show which experiments are relevant, which inputs are documented, and where evidence stops—not to certify a habitat or predict a fire.

## 3. Key Scientific & Technical Innovations

### 3.1 Five habitat and research-screening presets

The labels below are the user-facing scenario names; the profile labels are the exact names returned by the backend. Values are screening inputs, not mission requirements.

| Preset | Backend profile label | O2 (%) | Pressure (psi / atm) | PO2 (psi) | Airflow (cm/s) | Gravity (g) |
|---|---|---:|---:|---:|---:|---:|
| ISS USOS Cabin | ISS USOS standard cabin | 21.0 | 14.7 / 1.000 | 3.087 | 5–15 | 0.000 |
| Artemis Lunar Base | Lunar surface habitat screening profile | 34.0 | 10.2 / 0.694 | 3.468 | 8–20 | 0.166 |
| Mars Transit / Surface Habitat | Mars transit / surface screening profile | 26.5 | 11.8 / 0.803 | 3.127 | 10–10 | 0.376 |
| EVA Spacesuit | EVA suit screening profile | 100.0 | 4.3 / 0.293 | 4.300 | 15–30 | 0.166 |
| ACME CFI-G High-O2 Testbed | Oxygen-enrichment research envelope | 85.0 | 14.7 / 1.000 | 12.495 | 5–5 | 0.000 |

These are the five profiles in `backend/src/catalogue.py`. In particular, the lunar profile is not named “Pressurized Rover” in the implementation, and the EVA profile is not identified as a specific EMU configuration.

### 3.2 Partial-gravity bounding and E-FIELD analogy

The simulator places a deterministic visualization between 0g evidence (including BASS-II and ACME-BRE), 1g material-screening references, and the PSI-22 ACME E-FIELD ion-driven body-force analogy. It also labels **LUCI** (*Lunar-g Combustion Investigation*) and **FM2** (*Flammability of Materials on the Moon*) as future missions whose direct measurements are not present in this build.

The code uses a buoyant-velocity scale of `V_b = 28 * sqrt(g)` cm/s and combines it with selected airflow as `V_eff = sqrt(airflow^2 + V_b^2)`. At 0.166g, `V_b` is **11.41 cm/s**. The illustrative E-FIELD scaling maps gravity to `min(10 kV, 10 kV * sqrt(g))` across a 2.54 cm electrode gap: **4.07 kV**, or **1.60 kV/cm**, at 0.166g. The implementation explicitly says this is not a calibrated gravity-to-voltage conversion.

For clarity, the current screening MOC is computed as `clamp(MOC_ref - 1.1 * exp(-((g - 0.166) / 0.18)^2) + 0.035 * max(V_eff - 25, 0) + 0.20 * (3.087 - 0.21 * pressure_psi), 5, 35)`. `MOC_ref` is selected by a fuel-name heuristic (14% for selected liquid fuels, 16% for listed solids, and 12% for listed gases; otherwise 16%). This is a visualization formula, not a fitted or experimentally validated physical model.

For the dashboard's representative lunar inputs—34% O2, 10.2 psi, 14 cm/s airflow, and “Sibal cotton fiberglass”—the current surrogate returns:

| Gravity | Surrogate MOC output | Buoyant velocity |
|---:|---:|---:|
| 0g | 15.72% | 0.00 cm/s |
| 0.166g | 15.09% | 11.41 cm/s |
| 1g | 16.41% | 28.00 cm/s |

These are outputs of the code-defined heuristic, **not NASA measurements, a validated lunar flammability limit, a prediction, or a safety determination**. At the stated inputs the implementation returns 16.41% at 1g; values such as 16.38% or a purported measured 14.90–15.09% band should not be quoted as this run's exact output. LUCI and FM2 data are needed to test the partial-gravity hypothesis.

### 3.3 Evidence ranking and cross-investigation comparison

- **Deterministic matching:** rank explanations show the documented match or mismatch for each available scenario factor. The match score is `100 * sum(known factor scores) / number of known factor scores`; known factors have equal weight, and apparatus capability contributes 0.5 rather than being treated as an exact tested point.
- **Evidence coverage:** `100 * scored factors / applicable factors`, reported separately from the match score. Unknown catalogue fields are not silently inferred.
- **Physics proximity:** continuous O2, pressure, and airflow overlap is reported separately from the evidence match score; it is not folded into that score.
- **Comparator:** accepts **2–4** unique PSI IDs and extracts differences in rack, fuel phase, O2, pressure, airflow, gravity, sensors, and predictive variables. It compares catalogue records; it does not merge raw measurements.

The catalogue includes CIR, MSG, MDCA, and Cygnus hardware provenance (as well as the PSI-47 “ISS Cabin” descriptor). A shared rack or overlapping envelope does not make two experiments interchangeable.

### 3.4 PSI-101 SAME-R lineage and DAFT context

The local analysis covers archived Pyrell runs **Run_063, Run_064, Run_076, Run_084, Run_095, and Run_097**. The archive reconciler checks phase summaries, cycle sequences, exception and mixed-band identities, duplicate/missing cycles, source-row references, periodicity metrics, lag correlations, and candidate models. The API serves reconciled archived products and row/CSV-line references; it reports `raw_replay_performed: false` and does not include original measurement rows.

The synthesis describes SAME/SAME-R pyrolysis-smoke droplets around **0.1–0.5 um** and DAFT/cabin dust particles above about **1.0 um** as a useful discrimination context. These catalogue-level values are not a validated alarm threshold or deployed detector algorithm. Raw PSI-101 source CSVs are local-only and their redistribution terms are not established.

### 3.5 Terrestrial fire-safety transfer pathways

These are candidate research-to-application links recorded in the catalogue, not product qualification or field-effectiveness claims.

| Research lineage | Catalogue transfer pathway | Scope |
|---|---|---|
| FLEX (PSI-69) and associated MIST study | Fine-water-mist and clean-agent / halon-replacement research | Candidate suppressant research; not a recommendation for a specific extinguisher |
| SAME / SAME-R (PSI-102 / PSI-101) and DAFT (PSI-47) | Smoke-versus-dust discrimination for mine, industrial, marine, and tunnel detectors | Nuisance-alarm research; not a dust-proof detector certification |
| BASS / SAFFIRE (PSI-26 / PSI-98 / PSI-99) | PBI/Nomex firefighter turnout textiles, material screening, and large-space fire-growth correlations | Screening and research transfer; not protective-equipment certification |
| Lightweight firefighter SCBA air tanks | No explicit SCBA-cylinder transfer is encoded in the current catalogue | A possible future research question, not an implemented project finding |

## 4. Full NASA PSI Repository Coverage (24 Investigations · ~12.4 TB Scope)

NASA PSI scope accounting lists 24 combustion-science investigations and about 12.4 TB of aggregate repository material. FIRELYTICS deeply indexes the 14 records in Tier 1. Tier 2 supplies repository-completeness context only; it is not physics-indexed or used for ranking. The 12.4 TB is **not** a local download or processing-volume claim.

### Tier 1 — 14 deeply indexed investigations

Ranges below are the structured catalogue fields used by the app. “Capability up to” is an apparatus capability, not a claim that every point in that interval was tested. “Not stated” means the catalogue does not provide a range.

| PSI ID | Short name | Hardware rack | Fuel phase | O2 (%) | Pressure (psi) | Airflow (cm/s) | Research pillar | DOI / NASA record |
|---|---|---|---|---:|---:|---:|---|---|
| PSI-101 | SAME-R | MSG | Aerosol / Dust | 21–21 | 14.7–14.7 | 0–5 | Detection | [10.60555/2np7-jv14](https://doi.org/10.60555/2np7-jv14) |
| PSI-102 | SAME | MSG | Aerosol / Dust | 21–21 | 14.7–14.7 | 0–10 | Detection | [10.60555/gd4k-8h62](https://doi.org/10.60555/gd4k-8h62) |
| PSI-47 | DAFT | ISS Cabin | Aerosol / Dust | 21–21 | 14.7–14.7 | 0–0 | Detection | [10.60555/ztgj-d202](https://doi.org/10.60555/ztgj-d202) |
| PSI-26 | BASS | MSG | Solid | 13.5–21 | 14.7–14.7 | Capability up to 40; range not stated | Prevention; Suppression | [10.60555/58h4-dy80](https://doi.org/10.60555/58h4-dy80) |
| PSI-25 | BASS-II | MSG | Solid | 13.5–21 | 14.7–14.7 | Capability up to 40; range not stated | Prevention; Suppression | [10.60555/4qc4-de67](https://doi.org/10.60555/4qc4-de67) |
| PSI-98 | SAFFIRE-I | Cygnus Spacecraft | Solid | 21–21 | 14.7–14.7 | 20–20 | Prevention; Detection | [10.60555/0t15-1z43](https://doi.org/10.60555/0t15-1z43) |
| PSI-99 | SAFFIRE-II/III | Cygnus Spacecraft | Solid | 21–21 | 14.7–14.7 | 20–30 | Prevention; Detection | [10.60555/2chp-m469](https://doi.org/10.60555/2chp-m469) |
| PSI-20 | BRE (ACME-BRE) | CIR | Gaseous (Solid Emulator) | 15–40 | 7.35–14.7 | 0–5 | Prevention | [10.60555/vb93-3y72](https://doi.org/10.60555/vb93-3y72) |
| PSI-159 | CFI-G (ACME-CFI-G) | CIR | Gaseous | 21–85 | 7.35–14.7 | 0–5 | Prevention | [10.60555/cyt1-kh64](https://doi.org/10.60555/cyt1-kh64) |
| PSI-22 | E-FIELD (ACME E-FIELD Flames) | CIR | Gaseous | 18–30 | 14.7–14.7 | 0–25 | Prevention | [DOI pending — PSI-22 record](https://psi.nasa.gov/physci/repo/data/investigations/PSI-22) |
| PSI-69 | FLEX | CIR + MDCA | Liquid Droplet | 15–30 | 7.35–22.05 | 0–15 | Prevention; Suppression | [10.60555/mbq8-0451](https://doi.org/10.60555/mbq8-0451) |
| PSI-68 | FLEX-2/CFI | CIR + MDCA | Liquid Droplet | 14–30 | 7.35–22.05 | 0–5 | Suppression; Prevention | [10.60555/byp8-h018](https://doi.org/10.60555/byp8-h018) |
| PSI-107 | SPICE | MSG | Gaseous | 21–21 | 14.7–14.7 | 5.4–65 | Detection; Prevention | [10.60555/9kbh-e962](https://doi.org/10.60555/9kbh-e962) |
| PSI-106 | SLICE | MSG | Gaseous | 21–21 | 14.7–14.7 | 2–45 | Prevention | [10.60555/pm12-rg61](https://doi.org/10.60555/pm12-rg61) |

The DOI values are the catalogue's linked identifiers; PSI-22 is the exception. Record metadata and experimental-file licenses must be checked at the source before redistributing any download. The PSI-101 raw CSVs in this workspace have no separate redistribution license recorded.

### Tier 2 — 10 associated studies

| Scope key | Associated PSI study | Scope role |
|---|---|---|
| SOFIE | Solid Fuel Ignition and Extinction | High-pressure / high-oxygen solid flammability context |
| SAFFIRE-IV/V/VI | SAFFIRE IV / V / VI | Large-scale fire growth, smoke scrubbing, and atmospheric cleanup context |
| ACME-CLD | ACME Coflow Laminar Diffusion Flame (CLD Flame) | Soot and radiative-structure context |
| ACME-s-Flame | ACME Structure & Response of Spherical Diffusion Flames (s-Flame) | Spherical-flame extinction context |
| FLEX-2J | FLEX-2J | Joint droplet combustion and flame-spread context |
| FLEX-IT | FLEX-Italian (FLEX-IT) | Droplet burning and radiative-soot context |
| FSDC | Fiber Supported Droplet Combustion | Precursor droplet-burning context |
| MIST | Water-Mist Fire Suppression Experiment | Fine-water-mist research context |
| LSP | Laminar Soot Processes | Soot and radiative-loss context |
| CFE/ICF | CFE / ICF | Capillary/interfacial combustion and smoldering context |

**Future bounding targets:** LUCI (Lunar-g Combustion Investigation) and FM2 (Flammability of Materials on the Moon) are described by the project as upcoming partial-gravity targets. They are not additional members of the 24-study scope count, and this application claims no LUCI or FM2 data.

## 5. System Architecture & UI Workspaces

```text
+------------------------------------------------+
| Browser                                        |
| Next.js 16 / React 19 / TypeScript workbench   |
+------------------------+-----------------------+
                         | same-origin /api/backend/*
                         v
+------------------------------------------------+
| Next.js catch-all API proxy                    |
| frontend/app/api/backend/[...path]/route.ts    |
| forwards requests to BACKEND_URL               |
+------------------------+-----------------------+
                         | private backend URL
                         v
+------------------------------------------------+
| FastAPI scientific API                         |
| Catalogue / rank / comparison / screening      |
| SAME-R archive reconciler / CSV and HTML reports|
+------------------------------------------------+
```

### Ten interactive dashboard workspaces

1. **Mission & Habitat Simulator** - configure habitat and combustion-screening inputs.
2. **Catalogue & Comparison Matrix** - explore PSI records and compare investigation metadata.
3. **SI Fire-Safety Synthesis** - inspect evidence ranking and cross-investigation synthesis.
4. **PSI-101 SAME-R Telemetry & Lineage Lab** - review archived runs, cycle lineage, and checks.
5. **All-in-One Executive View** - review scenario, evidence, and archive summaries together.
6. **AI Scientific Research Assistant** - ask bounded research questions and inspect retrieved citations.
7. **ML Fire Research Lab** - review grouped model evaluation, explanations, and exploratory scores.
8. **Virtual Spacecraft Monitoring** - inspect synthetic or historical telemetry and rule-based alerts.
9. **Fire Suppression Digital Twin** - compare simulated intervention trajectories.
10. **Scientific Decision Support** - synthesize scenario, catalogue, telemetry, and model context.

### Four zero-chart-library visualization families

- **Chart A:** O2 / pressure flammability envelope.
- **Chart B:** partial-gravity and E-FIELD bounding curve.
- **Chart C:** multi-factor ranked evidence breakdown.
- **Chart D:** SAME-R phase-band agreement and DAFT aerosol-size discrimination.

The visualizations use browser-native SVG and HTML/CSS rather than a charting package; Chart C's evidence tracks are HTML/CSS, not SVG. The interface uses a high-contrast monochrome black-and-white design system, with Dark Mode as the default and a Light Mode toggle. The ambient laboratory and space backgrounds are `/assets/bg-lab.png` and `/assets/bg-space-dark.jpeg`; the logo is `/assets/fire-logo.webp`. The Developer modal and all ten workspaces are part of the dashboard.

## 6. Complete Repository Directory Structure

Generated dependency, build, and cache trees (`node_modules`, `.next`, `.venv-local`, `.tools`, `.vercel`, and Python caches) are intentionally omitted. Git-ignored workspace files such as `frontend/AGENTS.md` and `frontend/next-env.d.ts` are not part of the checked-in source tree.

```text
.
|-- README.md
|-- about.md                         # Team onboarding and architecture guide
|-- DECISIONS.md
|-- progress.md
|-- .gitignore
|-- start-firelytics.bat             # Windows launcher entry point
|-- start-local.ps1                  # Starts local FastAPI and Next.js services
|-- requirements.txt                 # Root product-test dependencies
|-- phase_reversal_telemetry_audit.py
|-- recover_phase_lineage.py         # Archive lineage utility
|-- vercel.json
|-- .streamlit/config.toml
|-- app/streamlit_app.py             # Legacy Streamlit interface
|-- backend/
|   |-- app/main.py                  # FastAPI app and core routes
|   |-- app/archive.py               # Reconciled SAME-R archive reader
|   |-- src/catalogue.py             # Catalogue and screening logic
|   |-- src/reporting.py             # CSV and HTML reports
|   |-- backend/ai/                 # Research agent, RAG and retrieval
|   |-- backend/ml/                 # Dataset registry, evaluation and inference
|   |-- backend/telemetry/          # Ingestion, streaming and anomaly rules
|   |-- backend/digital_twin/       # Fire-suppression simulation
|   |-- backend/decision_support/   # Cross-workspace synthesis
|   |-- data/catalogue/investigations.json
|   |-- data/metadata/                # Packaged archive and lineage products
|   `-- tests/                       # Backend API and telemetry tests
|-- data/
|   |-- catalogue/investigations.json
|   |-- metadata/                    # Provenance and inspection artifacts
|   `-- raw/PSI-101/                 # Optional source subset; Git-ignored
|-- docs/                            # Architecture, methods, validation and references
|-- frontend/
|   |-- app/api/backend/[...path]/route.ts
|   |-- app/ui/                   # frontend/app/ui/ workspace components
|   |   |-- dashboard.tsx
|   |   |-- charts.tsx
|   |   |-- model.ts
|   |   |-- ai-research-assistant.tsx
|   |   |-- ml-fire-research-lab.tsx
|   |   |-- virtual-spacecraft-monitoring.tsx
|   |   |-- fire-suppression-digital-twin.tsx
|   |   `-- scientific-decision-support.tsx
|   |-- app/page.tsx, layout.tsx, globals.css
|   |-- public/assets/               # Logo and workspace backgrounds
|   |-- scripts/next.mjs
|   |-- package.json
|   `-- package-lock.json
|-- src/                             # Root compatibility and analysis modules
`-- tests/test_product.py             # Product and provenance checks
```

The root `data/raw/PSI-101/` source files are local and Git-ignored. The backend serves reconciled archive products and source-row references from `backend/data/metadata/`; it does not bundle or replay the raw CSV measurements. The root `src/` modules support legacy/local workflows; the deployed FastAPI implementation is under `backend/`.

## 7. Quickstart & Local Installation Guide

### Prerequisites

- **Python 3.12–3.15** (`backend/pyproject.toml` requires `>=3.12,<3.16`).
- **Node.js 22.x** (`frontend/package.json` requires `>=22,<23`; Node 20 is not supported by this frontend manifest).
- npm, installed with Node.js.

### One-command Windows startup

From the repository root:

```powershell
.\start-firelytics.bat
```

The batch launcher checks for Python and Node.js, then delegates to `start-local.ps1`, which validates the supported Python 3.12–3.15 and Node.js 22 versions. It creates or reuses `.venv-local`, installs backend and frontend dependencies when needed, starts FastAPI on `http://127.0.0.1:8000` and Next.js on `http://localhost:3000`, checks the same-origin API proxy, and opens the frontend. Logs are written under `.local/logs/`. Press **Ctrl+C** to stop processes started by the launcher.

### Manual startup — two terminals

Open two terminals. Use Python 3.12–3.15 and Node.js 22.x.

**Terminal 1 — Backend (PowerShell):**

```powershell
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Frontend (PowerShell):**

```powershell
cd frontend
npm install
$env:BACKEND_URL = "http://127.0.0.1:8000"
npm run dev
```

Open `http://127.0.0.1:3000`. FastAPI's interactive API documentation is at `http://127.0.0.1:8000/docs`.

For a production frontend on the same host, keep `BACKEND_URL` set and run `npm run build` followed by `npm start` from the `frontend/` directory.

**macOS / Linux equivalents:** In Terminal 1, run `cd backend`, `python3 -m pip install -r requirements.txt`, then `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`. In Terminal 2, run `cd frontend`, `npm install`, then `BACKEND_URL=http://127.0.0.1:8000 npm run dev`.

### Optional legacy Streamlit workflow

The root `requirements.txt` is for the legacy Streamlit path, not the FastAPI backend:

```bash
python -m pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Raw replay and source-row checks require the local PSI-101 CSV subset. Those raw files are not tracked or redistributed by this repository; follow the PSI source record and applicable file terms before acquiring them.

## 8. REST API Reference

The API is served by FastAPI at `http://127.0.0.1:8000`. The browser calls it through the same-origin Next.js proxy at `/api/backend/*`; for example, `/api/backend/investigations` forwards to backend `/investigations`. The proxy uses `BACKEND_URL`.

| Method | FastAPI path | Request | Response |
|---|---|---|---|
| `GET` | `/health` | — | Service status, catalogue count, archive validation, raw-replay availability |
| `GET` | `/investigations` | — | `items` catalogue and `repository_scope` |
| `GET` | `/investigations/{investigation_id}` | PSI ID, e.g. `PSI-101` | One catalogue record |
| `GET` | `/repository/scope` or `/api/repository/scope` | — | 24-study / ~12.4 TB scope accounting |
| `GET` | `/habitats` or `/api/habitats` | — | Five research-screening profiles and interpretation |
| `POST` | `/scenarios/rank` | `Scenario` JSON | Ranked catalogue records and scoring explanation |
| `POST` | `/simulate` or `/api/simulate` | `SimulationScenario` JSON | Scenario, surrogate metrics, ranked records, synthesis, limitations |
| `POST` | `/compare` or `/api/compare` | 2–4 unique `psi_ids`; optional scenario | Comparison matrix, deltas, synthesis |
| `GET` | `/samer/runs` | — | Six run summaries |
| `GET` | `/samer/runs/{run_id}/validation` | Run ID, e.g. `95` | Archived reconciliation checks; `raw_replay_performed: false` |
| `GET` | `/samer/runs/{run_id}/summary` | Run ID | Phase/periodicity summary, lags, models, cycle counts, exceptions |
| `GET` | `/samer/runs/{run_id}/cycles/{cycle_id}` | Run and cycle IDs | Archived cycle classification and source-row references |
| `POST` | `/reports/csv` | `Scenario` JSON | Downloadable CSV report |
| `POST` | `/reports/html` | `Scenario` JSON | Downloadable HTML report |
| `GET` | `/ai/status`, `/api/ai/status` | — | Local Ollama status and RAG corpus summary |
| `GET/POST` | `/ai/*` and `/api/ai/*` | AI task-specific JSON | Retrieval, chat, explanations, reports, and history |
| `GET/POST` | `/ml/*` and `/api/ml/*` | Dataset, prediction, or model ID | Dataset registry, grouped-model metrics, predictions, and explainability |
| `GET/POST` | `/telemetry/*` and `/api/telemetry/*` | Mode, stream, or CSV upload | Synthetic/replay telemetry and rule/statistical anomaly log |
| `POST` | `/digital-twin/simulate`, `/api/digital-twin/simulate` | Baseline and intervention JSON | Exploratory environment-boundary comparison |
| `POST` | `/decision-support/synthesize`, `/api/decision-support/synthesize` | Scenario and subsystem snapshots | Evidence-linked, deterministic research brief |

There are no FastAPI `/api/health`, `/api/catalogue`, or `/api/rank` routes. The rank endpoint is `/scenarios/rank`; the Next proxy prefix is `/api/backend/`.

### Example requests and response shapes

Health and catalogue:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/investigations
```

`POST /simulate`:

```bash
curl -X POST http://127.0.0.1:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "o2_pct": 34,
    "pressure_psi": 10.2,
    "airflow_cms": 14,
    "gravity_g": 0.166,
    "gravity_regime": "Lunar partial gravity",
    "material": "Sibal cotton fiberglass",
    "mission": "Lunar habitat screening"
  }'
```

The response contains `scenario`, `simulation.model`, `simulation.metrics`, `gravity_curve`, `o2_pressure_envelope`, `ranked_investigations`, `synthesis`, and an interpretation that the physics output is a visualization surrogate—not a validated prediction or safety assessment.

`POST /scenarios/rank`:

```json
{
  "mission": "ISS baseline",
  "gravity": "Microgravity",
  "oxygen_pct": 21,
  "pressure_atm": 1,
  "airflow_cm_s": 10,
  "material": "PMMA",
  "pillar": "Prevention"
}
```

`POST /compare`:

```json
{
  "psi_ids": ["PSI-25", "PSI-20", "PSI-22"],
  "scenario": {
    "mission": "Lunar screening",
    "gravity": "Lunar partial gravity",
    "oxygen_pct": 34,
    "pressure_atm": 0.694,
    "airflow_cm_s": 14,
    "material": "Sibal cotton fiberglass",
    "pillar": "Prevention"
  }
}
```

The comparison response includes `matrix`, automatically extracted `deltas`, and a synthesis whose interpretation cautions that pending candidates need primary-source verification.

SAME-R cycle provenance:

```bash
curl http://127.0.0.1:8000/samer/runs/95/cycles/8677
```

The archived example identifies `Run_095/HKPData_gmt250_4.csv`, source data row `1201`, and CSV line `1202`. It returns references only; original raw measurement values are not packaged.

For report downloads, send a `Scenario` body to `/reports/csv` or `/reports/html`; both endpoints return an attachment. Use the same `Scenario` fields shown for `/scenarios/rank`.

## 9. Automated Verification, Testing & Scientific Guardrails

Run from the repository root:

```bash
python -m pytest -q
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

The frontend `typecheck` script runs `tsc --noEmit`. The current Python suite contains 41 tests across root product/provenance checks and backend API tests. The raw PSI-101 replay/provenance checks require the local source CSV subset under `data/raw/PSI-101/`; those files are intentionally Git-ignored. Without those locally supplied files, raw-replay-dependent tests cannot be reproduced from a clean clone. The backend API itself uses the reconciled archive products and does not replay raw rows.

The local ML registry and three versioned JSON model artifacts are also Git-ignored pending PSI-101 source-file and derived-model rights review. The local API works when those files are present, but Git-based deployments do not include them; production ML inference requires an approved artifact delivery or storage mechanism. See the [Phase 3 model report](docs/PHASE3_MODEL_REPORT.md) for the exact artifact paths, sizes, grouped metrics, and verification limits.

### Scientific integrity and epistemic guardrails

- **Source data versus inference:** NASA PSI catalogue descriptions, record identifiers, linked DOIs, and the archived SAME-R cycle ledger are distinguished from the app's calculated outputs.
- **No fabricated coverage:** 14 records are deeply indexed; 10 associated studies are scope context. Only the six named PSI-101 Pyrell runs are locally analyzed. The ~12.4 TB figure is repository-level context.
- **Surrogate is not a validated model:** the API returns `validated: false`. MOC, flame spread, flammability index, envelopes, and partial-gravity curves are deterministic visualization/screening surrogates, not NASA measurements, engineering design limits, fire predictions, or safety assessments.
- **Partial gravity is a hypothesis:** the lunar curve is bounded by 0g studies, 1g screening, and an illustrative PSI-22 E-FIELD analogy. It is not a measurement at lunar gravity. LUCI and FM2 measurements are needed to test it.
- **E-FIELD is not a calibrated gravity substitute:** the code describes the voltage/field relation as illustrative and requires test-matrix and ion-current/flow data before claiming equivalence.
- **Ranking is not safety scoring:** evidence match, coverage, and physics proximity describe catalogue support and scenario similarity. None is a fire-risk probability or safety rating.
- **Archive provenance is references-only:** the API reconciles stored archive outputs and returns exact cycle/source-row references, but reports `raw_replay_performed: false`; it does not ship the original source rows.
- **Licensing:** the metadata records PSI record metadata as CC0-1.0, but that does not establish a license for every downloadable data file. Check the source record and file-specific terms before redistribution.

## 10. The Team Behind The Mission (Developers)

The following names, roles, and available profile links match the in-app Developer modal.

| Team member | Role | Links |
|---|---|---|
| **Chandan Kumar Sah** | Project Lead & Backend Engineer | [GitHub](https://github.com/Chandan24-cell) · [LinkedIn](https://www.linkedin.com/in/chandan-kumar-sah-40156a360/) |
| **Saurav Shah Teli** | Frontend & Dashboard Visualization | [GitHub](https://github.com/Saurav924-sks) · [LinkedIn](https://www.linkedin.com/in/saurav-shah-aa1a64357/) |
| **Mantu Kumar Chaurasiya** | Data Engineering & Dataset Curation | [GitHub](https://github.com/mantuchaurasiya092-source) · [LinkedIn](https://www.linkedin.com/in/mantu-kumar-chaurasiya-117594438/) |
| **Bhola Sah** | Quality Assurance & Testing | [GitHub](https://github.com/bholasah) · [LinkedIn](https://www.linkedin.com/in/bhola-sah-90585244b/) |
| **Digambar Updahaya** | Scientific Research & Documentation | — |
| **Aakash** | Team Member | Profile pending |

## 11. NASA Data Provenance, Disclaimers & References

- [NASA Physical Science Informatics (PSI)](https://psi.nasa.gov/)
- [NASA — A Researcher's Guide to: Combustion Science](https://www.nasa.gov/missions/station/a-researchers-guide-to-combustion-science/)
- [NASA PSI catalogue references and licenses](docs/references.md)
- [NASA-hosted paper: Challenges and Research Needs for Micro- and Partial-Gravity Fires](https://science.nasa.gov/wp-content/uploads/2023/05/60_afb22b1e538432728848e83bb3ade8c2_LiaoYaTingT.pdf)
- [NASA Space Apps Challenge](https://www.spaceappschallenge.org/)

FIRELYTICS AI is an independent research prototype. Its outputs are for research exploration and must not be used as spacecraft design guidance, flight rules, fire-protection certification, or operational safety advice.

**NASA Space Apps Challenge non-endorsement disclaimer:** NASA does not endorse any non-U.S. Government entity and is not responsible for information contained on non-U.S. Government websites. For non-U.S. Government websites, participants must comply with any data use parameters of that specific website.

