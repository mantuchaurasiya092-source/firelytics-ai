# Migration validation record

Executed 2026-11-14 in the provided Windows workspace.

## Automated checks

- `python -m pytest -q`: **12 passed** (six root provenance/physics/report/Streamlit checks plus six FastAPI checks). One Starlette deprecation warning is emitted by TestClient; no failures.
- API tests cover health, the 14-record catalogue, deterministic scenario ranking and 422 input validation, six-run archive validation, cycle source-row references against local raw data, and CSV/HTML status/content. The Phase 3 scope endpoint and report sections were additionally smoke-tested through the Next.js proxy.
- `python -m compileall -q backend/app backend/src backend/tests`: passed.
- `npm ci` in `frontend/`: passed; 29 packages installed, audit reported 0 vulnerabilities.
- `npm run typecheck`: passed.
- `npm run build`: passed with Next.js 16.4.6 / Node 22.23.5. `/` is statically rendered and `/api/backend/[...path]` is a server route. The build ran through the telemetry-disabled wrapper.
- Catalogue metadata values, JSON format and source references have automated checks; all 14 deeply indexed PSI records were reconciled against their NASA PSI pages and DOI records.

## Local service integration

Ran FastAPI with Uvicorn and Next.js together, using a local `BACKEND_URL` to exercise the same-origin proxy. Results:

| Check | Result |
|---|---|
| Next.js root dashboard | HTTP 200; dashboard shell present |
| Proxied backend health | HTTP 200; archive checks passed; reports raw replay unavailable |
| Investigations | 14 real catalogue records returned |
| Repository scope | 24 investigations · ~12.4 TB · 14 deeply indexed + 10 associated returned |
| SAME-R runs | 63, 64, 76, 84, 95, 97 returned |
| Run 95 archived summary | 40 lag rows and 13 candidate-model rows returned |
| Run 95 cycle 8677 | exact source filename, source data row 1201 and CSV line 1202 returned; no measurement values packaged |
| Scenario ranking | ISS/Pyrell/Detection ranked PSI-101 first; Lunar/methanol/Suppression ranked PSI-69 first |
| CSV report | HTTP 200, `text/csv`, 37,425 bytes; habitat parameters and scope columns present |
| HTML report | HTTP 200, `text/html`, 29,949 bytes; habitat table and 14 + 10 scope matrix present |

These are direct local Next.js + FastAPI checks, not a Vercel private service-binding test and not browser-driven interaction.

## Archived checkpoint reconciliation

For each run, deployment startup checks archived classified count, exception count and exact cycle identities, mixed-cycle IDs and source-row references, duplicate count, first/last/unique cycle count, missing/gap counts and per-phase expected-band mapping counts against the archived checkpoints.

| Run | Archived classified cycles | Archived phase exceptions | Result |
|---:|---:|---:|---|
| 63 | 1,223 | 8 | PASS; all archive identity and count checks match |
| 64 | 1,504 | 6 | PASS; all archive identity and count checks match |
| 76 | 1,262 | 2 | PASS; all archive identity and count checks match |
| 84 | 1,262 | 185 | PASS; all archive identity and count checks match |
| 95 | 1,315 | 96 | PASS; all archive identity and count checks match |
| 97 | 1,320 | 0 | PASS; all archive identity and count checks match |

The API reports `verified_archived_outputs` and `raw_replay_performed: false`. It does not claim online raw CSV replay. Root tests independently run the preserved local raw replay and compare its cycle ledger against the archive.

## Vercel checks and blockers

- Vercel CLI **65.16.0** parsed `vercel.json` and detected `backend [FastAPI]` and `frontend [Next.js]` services.
- `vercel dev -L` (the CLI reports `-L` deprecated in favor of `--local`) failed before starting either service: Windows denied Vercel builder-cache dependency symlink creation with `EPERM: operation not permitted, symlink`. The direct local Next/FastAPI proxy test above is the fallback verification.
- `vercel build` was attempted. It stopped with `project_settings_required`: the project is not linked and there are no local Vercel project settings. No account/project was guessed or linked.
- Browser automation was unavailable; the rendered dashboard shell, service proxy and download response bodies were tested over HTTP, but no visual review or browser-triggered download was performed.
- The machine supplies Python 3.15.2, outside the configured Vercel-supported range. Attempting to provision Python 3.14 with `uv` downloaded an interpreter but the Windows environment refused to execute it. API tests therefore ran on Python 3.15.2, not the target Vercel Python 3.14 runtime.
- Vercel Services access and the Vercel Python runtime are Beta/account prerequisites. No credentials, linked project, Preview deployment, Production deployment or deployment URL were available; **no deployment is claimed**.

## Data and file integrity

- Raw source CSVs total **3,863,573 bytes** and are not bundled because their redistribution terms are not recorded.
- The deployed archived metadata/checkpoint payload totals **937,919 bytes**. It contains the cycle ledger and sanitized identity/reference extracts, not original measurement rows.
- Existing raw CSVs and original root archived outputs were not rewritten. New backend copies retain source archive bytes where included; new sanitized extracts contain only exception cycle IDs, mixed-cycle IDs, and mixed source-row references.
- The app has no persistent write path; exports are generated in memory. The downloaded CSV and HTML each remained well below Vercel's 4.5 MB Function response limit.
- The project has no `.vercel` linkage or secrets. Private `BACKEND_URL` is injected by Vercel Services; the local integration used only a temporary loopback value.
