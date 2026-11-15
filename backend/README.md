# FIRELYTICS AI backend

FastAPI service root for Vercel Services. Python serves the NASA PSI catalogue and uses the existing Python ranker/report builder. SAME-R online responses read the archived cycle sequence and reconcile it against the archived phase summary, exact exception identities, mixed rows and duplicate counts. Original raw CSV files are intentionally omitted because redistribution rights have not been established; the service clearly labels the output as archived and does not claim a fresh raw replay.

Local API: `uvicorn app.main:app --reload` from this directory after `python -m pip install -r requirements-dev.txt`. The deployment manifest stays lean in `requirements.txt`.
