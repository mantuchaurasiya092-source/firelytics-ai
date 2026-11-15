# Vercel migration, setup and current verification

## Target

The project is configured as a single Vercel Services deployment. Public traffic is routed to Next.js. FastAPI is a private service and the frontend reaches it through the service-bound `BACKEND_URL` and a same-origin Next.js route handler. The configuration matches the [Vercel Python backend guide](https://vercel.com/kb/guide/python-backend-on-vercel).

Vercel’s current Services feature is in Beta and requires Services access for the Vercel account; the Python Functions runtime is also Beta. The project must be set to the **Services** framework in Vercel project settings. These are account-side prerequisites, not repository settings. See [Vercel Services](https://vercel.com/docs/services) and [Python runtime](https://vercel.com/docs/functions/runtimes/python).

## Versions and manifests

- Node.js 22.x; frontend is pinned to Next.js 16.4.6 and React 19.3.1 in `frontend/package.json` and `frontend/package-lock.json`.
- Backend requests Python 3.14 using `backend/.python-version`; `backend/pyproject.toml` constrains the supported deployment range to Python 3.12–3.14.
- Runtime Python dependencies are limited to pinned FastAPI 0.117.1 in `backend/requirements.txt` / `backend/pyproject.toml`. Test/local-server dependencies are separate in `backend/requirements-dev.txt`.
- The existing app path uses standard-library CSV processing; no pandas or PyArrow dependency is included in either service bundle.
- Next.js telemetry is disabled by `frontend/scripts/next.mjs` for local build/dev processes. The app makes no automatic NASA, SI or font fetch. The Vercel backend binding is private and no secret is required.

## Dataset and bundle decision

The six raw source CSVs referenced by the historical replay total **3,863,573 bytes**. This repository does not establish the local files’ redistribution terms, so none of those raw files is placed under `backend/` or returned by its API.

Instead, the backend packages the already validated 2026-11-14 cycle sequence and summary outputs plus sanitized checkpoint extracts: only exception cycle IDs and mixed-cycle/source-row references are included where the original archived CSVs also held measured values. The archived metadata directory in `backend/data/metadata/` totals **937,919 bytes**. At process initialization the backend checks all six runs for classified counts, exception counts and exact exception cycle identities, mixed-cycle identities/source-row references, duplicate-cycle counts and unique cycle counts. It refuses to serve SAME-R data if any check fails.

The deployed status is **verified archived output; raw CSV replay was not performed**. Per-cycle API responses contain exact source filename, data-row number and CSV line number, while omitting original measurement row values. The local Streamlit/Python tools continue to perform full raw-file replay; their existence must not be confused with the deployed processing status.

## API and storage

FastAPI exposes `/health`, `/investigations`, `/investigations/{id}`, `/scenarios/rank`, `/samer/runs`, `/samer/runs/{run_id}/summary`, `/samer/runs/{run_id}/cycles/{cycle_id}`, `/samer/runs/{run_id}/validation`, `/reports/csv` and `/reports/html`. Browser requests use `/api/backend/*` and are proxied by the Next.js Route Handler. Its destination is only the server-side private `BACKEND_URL`.

No database or filesystem write is used. Reports are built in memory. Vercel Functions have a 500 MB uncompressed Python bundle allowance under the current runtime documentation and a 4.5 MB request/response payload limit; see [Function limits](https://vercel.com/docs/functions/limitations). The packaged archived evidence is below 1 MB, and current API responses/reports are small. The app has no upload endpoint; if large uploads are added later, send them directly to object storage rather than through a Function.

Vercel Functions use a read-only deployed filesystem apart from temporary storage. This design only opens packaged files for reading and does not rely on persistence.

## Local commands

Install Node.js 22, Python 3.14 and Git. The Vercel CLI can be run with `npx`; a global install is not required. Open PowerShell at the repository root. If this workspace has the portable Node runtime under `.tools`, add it to this PowerShell process first (this change does not persist after the window closes):

```powershell
$nodeDir = Join-Path (Get-Location) '.tools\node-v22.23.5-win-x64'
if (Test-Path (Join-Path $nodeDir 'npm.cmd')) {
    $env:Path = "$nodeDir;$env:Path"
}
node --version
npm.cmd --version
```

If Node.js is installed normally instead, make sure its installation directory is on `PATH`, then open a new PowerShell window. Install frontend dependencies from the frontend lockfile, and backend development dependencies separately:

```powershell
npm.cmd ci --prefix frontend
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
cd ..
npx.cmd --yes vercel@65.16.0 --version
npx.cmd --yes vercel@65.16.0 dev --local
```

Use `npm.cmd` and `npx.cmd` in PowerShell to avoid script execution-policy ambiguity. Do not run `npm install` at the repository root: the frontend dependencies are managed by `frontend/package-lock.json`. Local `vercel dev --local` starts both services and injects the local private binding without Vercel cloud environment pulls when the local Windows environment permits Vercel's builder setup. This workspace previously blocked builder-cache symlink creation with `EPERM`; if that still occurs, use the direct local integration instructions below. For direct development without Vercel CLI, run `uvicorn app.main:app --reload --port 8000` from `backend/` and `npm.cmd run dev` from `frontend/` with the server-only environment value `$env:BACKEND_URL = 'http://127.0.0.1:8000'`.

Run checks:

```powershell
python -m pytest -q
python -m pytest backend/tests -q
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

## Vercel project setup and deploy

1. Request/enable Vercel Services and Python runtime access for the account.
2. Import or link this repository at its root, then set Project Framework to **Services**. Do not set a service root as the overall project root; `vercel.json` owns the two service roots.
3. From the root, link and deploy a Preview:

   ```powershell
  npx.cmd --yes vercel@65.16.0 link
  npx.cmd --yes vercel@65.16.0 deploy
   ```

4. In Preview, check that `/` serves Next.js, `/api/backend/health` reports the archive checks passed and says raw replay was not performed, scenario ranking responds, all six run summaries load, cycle references are returned, and CSV/HTML downloads include scenario, factors, source links and limitations.
5. Only after Preview review, run `npx.cmd --yes vercel@65.16.0 deploy --prod` from the reviewed commit. No production deployment has been attempted from this environment.

The frontend service binding injects `BACKEND_URL`; do not add a `NEXT_PUBLIC_BACKEND_URL`, expose FastAPI by a public rewrite, or paste a backend URL into browser code.

## Verification record and blockers

- Existing root suite: **5 passed** on 2026-11-14.
- New FastAPI suite: **6 passed** on Python 3.15.2 (local test environment), including all six archive checks, ranking validation, source row references cross-checked against local raw files, and report response headers/content.
- Next.js TypeScript typecheck: **passed**. Production Next.js build: **passed** using Next 16.4.6 / Node 22.23.5. This is a framework build, not a Vercel Services build.
- Vercel CLI 65.16.0 recognized both configured services. `vercel dev --local` did **not** start: the Windows execution environment denied the symlinks Vercel’s `builders-vlt` cache creates (`EPERM: operation not permitted, symlink`). Thus Vercel service binding integration is **not verified here**.
- The machine only exposes Python 3.15.2. An attempt to provision Python 3.14 for local Vercel-compatible testing was blocked by the machine’s application-control policy when `uv` tried to execute the downloaded interpreter. Vercel supports Python 3.14, so the pinned remote target remains valid but was not locally exercised on that runtime.
- No Vercel project is linked and this session has no Vercel account credentials or confirmation of Services Beta access. No Preview or Production URL exists and no deployment is claimed.
- Existing raw dataset and root archived outputs were not modified. Backend archived checkpoints are copies/sanitized new extracts; they do not overwrite source audit artifacts.
