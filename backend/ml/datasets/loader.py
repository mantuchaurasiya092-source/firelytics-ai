from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from ml.datasets.registry import (
    BACKEND_METADATA_ROOT,
    CATALOGUE_PATH,
    RAW_PYRELL_ROOT,
    ROOT,
    WORKSPACE_METADATA_ROOT,
)


_CYCLE_SEQUENCE_FILES = {
    "181648": BACKEND_METADATA_ROOT
    / "PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_181648.csv",
    "183947": WORKSPACE_METADATA_ROOT
    / "PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_183947.csv",
}
_REQUIRED_CYCLE_FIELDS = {
    "RunID",
    "Cycle",
    "RelativeCyclePhase",
    "ExpectedBand",
    "ObservedBand",
    "ExceptionIndicator",
    "SourceRowCount",
    "MixedBandIndicator",
    "DuplicateCycleIndicator",
    "DuplicateRowCount",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader)


def _safe_repository_file(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError("Dataset path escapes the repository root.")
    if not resolved.is_file():
        raise FileNotFoundError(f"Dataset file is not present locally: {resolved}")
    return resolved


def load_psi101_raw_run(run_id: str) -> list[dict[str, Any]]:
    """Load one locally present Pyrell raw CSV and attach explicit row provenance."""
    if not re.fullmatch(r"\d{1,3}", run_id):
        raise ValueError("run_id must be a numeric PSI-101 run identifier.")
    normalized_run_id = str(int(run_id))
    matches = sorted((RAW_PYRELL_ROOT / f"Run_{int(normalized_run_id):03d}").glob("*.csv"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected one local raw CSV for PSI-101 Run {normalized_run_id}; found {len(matches)}."
        )
    path = _safe_repository_file(matches[0])
    rows = _read_csv(path)
    if not rows:
        raise ValueError(f"PSI-101 Run {normalized_run_id} raw CSV contains no records.")
    return [
        {
            **row,
            "RunID": normalized_run_id,
            "_source_file": path.relative_to(ROOT).as_posix(),
            "_source_row": index,
        }
        for index, row in enumerate(rows, start=1)
    ]


def load_psi101_raw_runs(run_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Load all direct Run_NNN CSVs; quarantine files are deliberately excluded."""
    available = sorted(
        str(int(path.parent.name.removeprefix("Run_")))
        for path in RAW_PYRELL_ROOT.glob("Run_*/*.csv")
        if re.fullmatch(r"Run_\d{3}", path.parent.name)
    )
    selected = available if run_ids is None else list(dict.fromkeys(run_ids))
    absent = sorted(set(selected) - set(available))
    if absent:
        raise FileNotFoundError(f"PSI-101 raw runs are not locally available: {', '.join(absent)}")
    return [row for run_id in selected for row in load_psi101_raw_run(run_id)]


def load_cycle_sequence(version: str = "181648") -> list[dict[str, str]]:
    """Load a reconciled local cycle ledger; the default is the production-bundled snapshot."""
    if version not in _CYCLE_SEQUENCE_FILES:
        raise ValueError("Supported cycle sequence snapshots are 181648 (bundled) and 183947 (workspace).")
    path = _safe_repository_file(_CYCLE_SEQUENCE_FILES[version])
    rows = _read_csv(path)
    fields = set(rows[0]) if rows else set()
    missing = _REQUIRED_CYCLE_FIELDS - fields
    if missing:
        raise ValueError(f"Cycle ledger is missing required columns: {', '.join(sorted(missing))}")
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["RunID"], row["Cycle"])
        if key in seen:
            raise ValueError(f"Duplicate archived cycle key: Run {key[0]}, cycle {key[1]}.")
        seen.add(key)
    return rows


def load_catalogue_condition_matrix() -> list[dict[str, Any]]:
    """Load the 14 catalogue records; these are investigation envelopes, not raw tests."""
    _safe_repository_file(CATALOGUE_PATH)
    records = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("NASA PSI condition catalogue is empty or invalid.")
    if len({record.get("psi_id") for record in records}) != len(records):
        raise ValueError("NASA PSI condition catalogue has duplicate psi_id values.")
    return records


def load_metadata_csv(relative_path: str) -> list[dict[str, str]]:
    """Load an inspected metadata CSV only from the two approved local metadata roots."""
    candidate = (ROOT / relative_path).resolve()
    allowed_roots = (BACKEND_METADATA_ROOT.resolve(), WORKSPACE_METADATA_ROOT.resolve())
    if not any(candidate.is_relative_to(root) for root in allowed_roots):
        raise ValueError("Metadata CSV must be inside backend/data/metadata or data/metadata.")
    return _read_csv(_safe_repository_file(candidate))


def dataset_source_path(relative_path: str) -> Path:
    if relative_path.startswith("backend/"):
        candidate = (BACKEND_METADATA_ROOT.parents[1] / relative_path.removeprefix("backend/")).resolve()
    else:
        candidate = (ROOT / relative_path).resolve()
    approved_roots = (
        RAW_PYRELL_ROOT.resolve(),
        (ROOT / "data" / "raw" / "PSI-101" / "_quarantine").resolve(),
        BACKEND_METADATA_ROOT.resolve(),
        WORKSPACE_METADATA_ROOT.resolve(),
        CATALOGUE_PATH.resolve(),
    )
    if not any(candidate == root or root in candidate.parents for root in approved_roots):
        raise ValueError("Dataset source is outside the approved local data directories.")
    return _safe_repository_file(candidate)


def load_file_by_relative_path(relative_path: str) -> list[dict[str, str]]:
    path = dataset_source_path(relative_path)
    if path.suffix.lower() != ".csv":
        raise ValueError("Only inspected CSV sources can be loaded as tabular data.")
    return _read_csv(path)
