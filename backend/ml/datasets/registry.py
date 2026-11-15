from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
ROOT = BACKEND_ROOT.parent if BACKEND_ROOT.name == "backend" else BACKEND_ROOT
CATALOGUE_PATH = BACKEND_ROOT / "data" / "catalogue" / "investigations.json"
RAW_PYRELL_ROOT = ROOT / "data" / "raw" / "PSI-101" / "Pyrell"
QUARANTINE_ROOT = ROOT / "data" / "raw" / "PSI-101" / "_quarantine"
BACKEND_METADATA_ROOT = BACKEND_ROOT / "data" / "metadata"
WORKSPACE_METADATA_ROOT = ROOT / "data" / "metadata"
if WORKSPACE_METADATA_ROOT.resolve() == BACKEND_METADATA_ROOT.resolve():
    WORKSPACE_METADATA_ROOT = ROOT / "_workspace_data_not_bundled" / "metadata"
ARCHIVE_CYCLE_FILE = (
    BACKEND_METADATA_ROOT
    / "PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_181648.csv"
)

PSI101_CONDITIONS = {
    "fuel_or_sample": "Pyrell® intumescent fire-retardant foam (Foamex) in the locally present Pyrell subset",
    "platform": "International Space Station, Microgravity Science Glovebox (MSG)",
    "oxygen": "Approximately 21% O2 by volume in cabin atmosphere; no numeric test matrix in the overview",
    "pressure": "Approximately 14.7 psi cabin pressure; not a varied test parameter in the overview",
    "airflow": "Quiescent heating with 0–5 cm/s residual flow in the overview; per-row flow channels require interpretation",
}

_DATACITE_VERIFIED_DOIS = {
    "10.60555/2np7-jv14",
    "10.60555/gd4k-8h62",
    "10.60555/ztgj-d202",
    "10.60555/58h4-dy80",
    "10.60555/4qc4-de67",
    "10.60555/0t15-1z43",
    "10.60555/2chp-m469",
    "10.60555/cyt1-kh64",
    "10.60555/mbq8-0451",
    "10.60555/byp8-h018",
    "10.60555/9kbh-e962",
    "10.60555/pm12-rg61",
}
_DATACITE_NOT_FOUND_DOIS = {"10.60555/vb93-3y72"}
_DATACITE_CHECK_DATE = "2026-11-15"

_MISSING_TEXT = {"", "na", "n/a", "nan", "null", "none"}
_SENTINELS = {"-999", "-999.0"}
_CLASS_NAME_PARTS = (
    "runid",
    "runmode",
    "testnumber",
    "phase",
    "band",
    "exception",
    "mixed",
    "duplicatecycle",
    "status",
    "category",
    "label",
    "state",
    "power",
)
_TARGET_FIELDS = {
    "ExpectedBand",
    "ObservedBand",
    "RelativeCyclePhase",
    "ExceptionIndicator",
    "MixedBandIndicator",
    "DuplicateCycleIndicator",
    "DuplicateRowCount",
}


def unit_for_column(name: str) -> str | None:
    lowered = name.lower()
    exact_units = (
        ("mgperm3", "mg/m³"),
        ("ptpercc", "particles/cm³"),
        ("volts", "V"),
        ("degc", "°C"),
        ("ohms", "Ω"),
        ("sccm", "sccm"),
        ("lpm", "L/min"),
        ("psia", "psia"),
        ("psig", "psig"),
        ("kilopascal", "kPa"),
        ("elapsedtesttime(secs)", "s"),
        ("timestampseconds", "s"),
        ("timeseconds", "s"),
        ("elapsedseconds", "s"),
        ("autocorrelation", "dimensionless"),
        ("fraction", "dimensionless"),
        ("ratio", "dimensionless"),
    )
    for token, unit in exact_units:
        if token in lowered:
            return unit
    if "timestamp" in lowered or lowered == "time":
        return "timestamp / s"
    if lowered == "cycle" or lowered.endswith("cycle"):
        return "cycle index"
    if "pressure" in lowered and "psi" in lowered:
        return "psi"
    if "flow" in lowered and "cm_s" in lowered:
        return "cm/s"
    return None


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip().lower() in _MISSING_TEXT


def _is_sentinel(value: str | None) -> bool:
    return value is not None and value.strip().lower() in _SENTINELS


def _is_categorical_column(name: str) -> bool:
    lowered = name.lower()
    return any(part in lowered for part in _CLASS_NAME_PARTS)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _relative(path: Path) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(BACKEND_ROOT.resolve()):
        return "backend/" + resolved.relative_to(BACKEND_ROOT.resolve()).as_posix()
    return resolved.relative_to(ROOT.resolve()).as_posix()


def _read_catalogue() -> list[dict[str, Any]]:
    if not CATALOGUE_PATH.is_file():
        raise FileNotFoundError(f"NASA PSI catalogue is missing: {_relative(CATALOGUE_PATH)}")
    records = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("NASA PSI catalogue must be a JSON list.")
    return records


def inspect_csv(path: Path, dataset_id: str, storage_scope: str) -> dict[str, Any]:
    """Return file-level schema and quality facts computed from the current CSV."""
    blank_counts: Counter[str] = Counter()
    sentinel_counts: Counter[str] = Counter()
    class_counts: dict[str, Counter[str]] = {}
    run_counts: Counter[str] = Counter()
    time_deltas: list[float] = []
    previous_time: float | None = None
    fields: list[str] = []
    row_count = 0

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        class_fields = [name for name in fields if _is_categorical_column(name)]
        class_counts = {name: Counter() for name in class_fields}
        time_field = "Time" if "Time" in fields else None
        if time_field is None:
            time_field = next(
                (name for name in fields if name.endswith("TimestampSeconds")),
                None,
            )

        for row in reader:
            row_count += 1
            for name in fields:
                value = row.get(name)
                if _is_missing(value):
                    blank_counts[name] += 1
                elif _is_sentinel(value):
                    sentinel_counts[name] += 1
                if name in class_counts and not _is_missing(value):
                    class_counts[name][value.strip()] += 1
            run_id = row.get("RunID")
            if run_id and run_id.strip():
                run_counts[run_id.strip()] += 1
            if time_field:
                try:
                    current_time = float(row.get(time_field, ""))
                except (TypeError, ValueError):
                    previous_time = None
                else:
                    if previous_time is not None:
                        time_deltas.append(current_time - previous_time)
                    previous_time = current_time

    schema = []
    for name in fields:
        blank = blank_counts[name]
        sentinel = sentinel_counts[name]
        missing = blank + sentinel
        schema.append(
            {
                "name": name,
                "unit": unit_for_column(name),
                "record_count": row_count,
                "blank_count": blank,
                "sentinel_count": sentinel,
                "missing_count": missing,
                "missing_pct": round((100 * missing / row_count), 4) if row_count else None,
            }
        )

    missing_columns = {
        name: {
            "blank_count": blank_counts[name],
            "sentinel_count": sentinel_counts[name],
            "missing_count": blank_counts[name] + sentinel_counts[name],
            "missing_pct": round(
                100 * (blank_counts[name] + sentinel_counts[name]) / row_count, 4
            )
            if row_count
            else None,
        }
        for name in fields
        if blank_counts[name] or sentinel_counts[name]
    }
    positive_deltas = sorted(delta for delta in time_deltas if delta > 0)
    sampling_interval = None
    if positive_deltas:
        middle = len(positive_deltas) // 2
        median = positive_deltas[middle]
        if len(positive_deltas) % 2 == 0:
            median = (positive_deltas[middle - 1] + median) / 2
        sampling_interval = {
            "time_column": time_field,
            "positive_intervals": len(positive_deltas),
            "median_seconds": median,
            "minimum_seconds": positive_deltas[0],
            "maximum_seconds": positive_deltas[-1],
            "non_positive_intervals": len(time_deltas) - len(positive_deltas),
        }
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return {
        "dataset_id": dataset_id,
        "source_file": _relative(path),
        "storage_scope": storage_scope,
        "deployment_availability": (
            "bundled_in_production" if storage_scope == "backend_bundle" else "local_raw_only"
        ),
        "format": "CSV",
        "record_count": row_count,
        "column_count": len(fields),
        "sha256": digest.hexdigest(),
        "schema": schema,
        "missing_value_stats": missing_columns,
        "run_grouping": {
            "group_column": "RunID" if "RunID" in fields else None,
            "group_record_counts": dict(sorted(run_counts.items(), key=lambda item: item[0])),
            "group_count": len(run_counts),
        },
        "class_balance": {
            name: dict(sorted(counts.items()))
            for name, counts in class_counts.items()
            if counts
        },
        "sampling_interval_seconds": sampling_interval,
    }


def _provenance(psi_id: str, doi: str | None, source_url: str | None) -> dict[str, Any]:
    if psi_id != "PSI-101":
        license_note = (
            "NASA PSI catalogue metadata identifies CC0-1.0; verify the selected record and each "
            "individual file before redistribution."
        )
    else:
        license_note = (
            "DataCite record metadata is CC0-1.0. The local raw CSVs have no separate file-level "
            "license statement in this repository; redistribution permissions remain unverified."
        )
    doi_lower = (doi or "").lower()
    if doi_lower in _DATACITE_VERIFIED_DOIS:
        doi_status = "verified_in_datacite_at_check_date"
    elif doi_lower in _DATACITE_NOT_FOUND_DOIS:
        doi_status = "datacite_returned_404_at_check_date"
    elif doi and doi.lower().startswith("pending"):
        doi_status = "pending_in_catalogue"
    else:
        doi_status = "not_verified"
    return {
        "psi_id": psi_id,
        "official_url": source_url,
        "doi": doi,
        "doi_status": doi_status,
        "doi_verification_url": (
            f"https://api.datacite.org/dois/{doi}" if doi_lower.startswith("10.") else None
        ),
        "doi_checked_at": _DATACITE_CHECK_DATE,
        "license": license_note,
        "citation_requirement": "Cite the NASA PSI investigation record, DOI when verified, and the original source file/run when applicable.",
    }


def _raw_file_records() -> list[dict[str, Any]]:
    files = sorted(
        RAW_PYRELL_ROOT.glob("Run_*/*.csv"),
        key=lambda path: (path.parent.name, path.name),
    )
    records = []
    for path in files:
        match = re.fullmatch(r"Run_(\d+)", path.parent.name)
        if not match:
            continue
        run_id = str(int(match.group(1)))
        record = inspect_csv(
            path,
            f"psi101_raw_run_{run_id}",
            "workspace_raw",
        )
        record.update(
            {
                "dataset_name": f"PSI-101 SAME-R raw telemetry — Run {run_id}",
                "dataset_group": "psi101_raw_telemetry",
                "psi_id": "PSI-101",
                "provenance": _provenance(
                    "PSI-101",
                    "10.60555/2np7-jv14",
                    "https://psi.nasa.gov/physci/repo/data/investigations/PSI-101",
                ),
                "experimental_conditions": PSI101_CONDITIONS,
                "grouping_key": "RunID inferred from the Run_NNN directory; source CSV does not contain a RunID column.",
                "target_variables": [],
                "limitation": "Raw telemetry is available only in the local workspace and is not included in the backend deployment bundle.",
            }
        )
        records.append(record)
    return records


def _quarantine_records() -> list[dict[str, Any]]:
    files = sorted(QUARANTINE_ROOT.rglob("*.csv"))
    records = []
    duplicate_map = {
        "Run107_candidate_is_Test095": "Exact SHA-256 duplicate of PSI-101 Run 95; not an independent Run 107.",
        "Run107_duplicate_of_Run097": "Exact SHA-256 duplicate of PSI-101 Run 97; not an independent Run 107.",
    }
    duplicate_paths = {
        "Run107_candidate_is_Test095": RAW_PYRELL_ROOT / "Run_095" / "HKPData_gmt250_4.csv",
        "Run107_duplicate_of_Run097": RAW_PYRELL_ROOT / "Run_097" / "HKPData_gmt251_1.csv",
    }
    for path in files:
        group = path.parent.name
        record = inspect_csv(
            path,
            f"psi101_quarantine_{_slug(group)}",
            "workspace_quarantine",
        )
        record.update(
            {
                "dataset_name": f"Quarantined PSI-101 candidate — {group}",
                "dataset_group": "psi101_quarantine",
                "psi_id": "PSI-101",
                "deployment_availability": "excluded_quarantine_local_only",
                "quarantined": True,
                "exclusion_reason": duplicate_map.get(group, "Quarantined; not eligible for ingestion without review."),
                "duplicate_of": (
                    _relative(duplicate_paths[group])
                    if group in duplicate_paths and duplicate_paths[group].is_file()
                    else None
                ),
                "sha256_duplicate_confirmed": (
                    path.is_file()
                    and group in duplicate_paths
                    and duplicate_paths[group].is_file()
                    and record["sha256"]
                    == hashlib.sha256(duplicate_paths[group].read_bytes()).hexdigest()
                ),
                "provenance": _provenance(
                    "PSI-101",
                    "10.60555/2np7-jv14",
                    "https://psi.nasa.gov/physci/repo/data/investigations/PSI-101",
                ),
            }
        )
        records.append(record)
    return records


def _metadata_records() -> list[dict[str, Any]]:
    records = []
    roots = (
        ("backend_bundle", BACKEND_METADATA_ROOT),
        ("workspace_derived", WORKSPACE_METADATA_ROOT),
    )
    for storage_scope, directory in roots:
        for path in sorted(directory.glob("*.csv")):
            dataset_id = f"{storage_scope}_{_slug(path.stem)}"
            record = inspect_csv(path, dataset_id, storage_scope)
            record.update(
                {
                    "dataset_name": path.stem,
                    "dataset_group": (
                        "psi101_reconciled_archive"
                        if "Periodicity_CycleSequence" in path.name
                        else "psi101_derived_metadata"
                    ),
                    "psi_id": "PSI-101",
                    "provenance": _provenance(
                        "PSI-101",
                        "10.60555/2np7-jv14",
                        "https://psi.nasa.gov/physci/repo/data/investigations/PSI-101",
                    ),
                    "experimental_conditions": PSI101_CONDITIONS,
                    "target_variables": (
                        [
                            "ExceptionIndicator",
                            "MixedBandIndicator",
                            "ObservedBand",
                        ]
                        if "Periodicity_CycleSequence" in path.name
                        else []
                    ),
                    "limitation": (
                        "Archived/reconciled output, not raw measurement replay. Labels inherit the documented "
                        "DustTrak-A band and historical phase rules."
                        if "Periodicity_CycleSequence" in path.name
                        else "Derived audit product; not an independent NASA outcome table."
                    ),
                }
            )
            records.append(record)
    return records


def _catalogue_record(records: list[dict[str, Any]]) -> dict[str, Any]:
    fields = (
        ("psi_id", None),
        ("name", None),
        ("doi", None),
        ("source_url", None),
        ("research_area", None),
        ("o2_range_pct", "%"),
        ("pressure_range_psi", "psi"),
        ("airflow_range_cm_s", "cm/s"),
        ("hardware_rack", None),
        ("fuel_phase", None),
        ("gravity_regimes", None),
        ("fuel_or_sample", None),
        ("platform", None),
    )
    missing = {
        name: sum(record.get(name) in (None, "", []) for record in records)
        for name, _unit in fields
    }
    return {
        "dataset_id": "psi_catalogue_tier1_conditions",
        "dataset_name": "NASA PSI Catalogue Condition Matrix — Tier 1",
        "dataset_group": "psi_catalogue",
        "source_file": _relative(CATALOGUE_PATH),
        "format": "JSON",
        "record_count": len(records),
        "column_count": len(fields),
        "schema": [
            {
                "name": name,
                "unit": unit,
                "record_count": len(records),
                "missing_count": missing[name],
                "missing_pct": round(100 * missing[name] / len(records), 4) if records else None,
            }
            for name, unit in fields
        ],
        "condition_fields": [
            {"name": name, "unit": unit}
            for name, unit in fields
            if name in {
                "o2_range_pct",
                "pressure_range_psi",
                "airflow_range_cm_s",
                "hardware_rack",
                "fuel_phase",
                "gravity_regimes",
                "research_area",
            }
        ],
        "missing_value_stats": {
            name: {
                "missing_count": count,
                "missing_pct": round(100 * count / len(records), 4) if records else None,
            }
            for name, count in missing.items()
            if count
        },
        "records": [
            {
                **record,
                "provenance": _provenance(
                    record.get("psi_id", ""),
                    record.get("doi"),
                    record.get("source_url"),
                ),
            }
            for record in records
        ],
        "deployment_availability": "bundled_in_production",
        "license": "NASA PSI record metadata is identified as CC0-1.0 in the local catalogue; individual source files require their own rights review.",
        "target_variables": [],
        "limitation": "Catalogue condition envelopes are not per-test measurement rows or labeled combustion outcomes.",
    }


def _other_local_artifacts() -> list[dict[str, Any]]:
    raw_root = ROOT / "data" / "raw" / "PSI-101"
    return [
        {
            "source_file": _relative(path),
            "format": path.suffix.lstrip(".").upper(),
            "size_bytes": path.stat().st_size,
            "processing_status": "local non-tabular source; not parsed as a measurement table",
        }
        for path in sorted(raw_root.rglob("*"))
        if path.is_file() and path.suffix.lower() not in {".csv"}
    ]


def build_dataset_registry() -> dict[str, Any]:
    """Inspect local datasets without downloading or claiming unavailable PSI files."""
    catalogue = _read_catalogue()
    raw_records = _raw_file_records()
    quarantine_records = _quarantine_records()
    metadata_records = _metadata_records()
    catalogue_record = _catalogue_record(catalogue)

    raw_total = sum(record["record_count"] for record in raw_records)
    raw_groups = {
        record["dataset_id"].rsplit("_", 1)[-1]: record["record_count"]
        for record in raw_records
    }
    archive_record = next(
        (
            record
            for record in metadata_records
            if record["source_file"]
            == "backend/data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_181648.csv"
        ),
        None,
    )
    external = [
        {"name": "BASS-II", "psi_ids": ["PSI-25"]},
        {"name": "SAFFIRE", "psi_ids": ["PSI-98", "PSI-99"]},
        {"name": "FLEX", "psi_ids": ["PSI-69", "PSI-68"]},
        {"name": "SPICE", "psi_ids": ["PSI-107"]},
        {"name": "SLICE", "psi_ids": ["PSI-106"]},
        {"name": "ACME", "psi_ids": ["PSI-20", "PSI-22", "PSI-159"]},
    ]
    for item in external:
        item.update(
            {
                "raw_tabular_files_local": 0,
                "availability": "catalogue_metadata_only",
                "limitation": "No raw per-test measurement table was found in the repository's inspected local data directories.",
            }
        )

    datasets = [
        {
            "dataset_id": "psi101_raw_telemetry",
            "dataset_name": "PSI-101 SAME-R raw Pyrell telemetry runs",
            "dataset_group": "psi101_raw_telemetry",
            "psi_id": "PSI-101",
            "record_count": raw_total,
            "file_count": len(raw_records),
            "run_grouping": {
                "group_column": "RunID inferred from Run_NNN directory",
                "group_record_counts": raw_groups,
                "group_count": len(raw_groups),
            },
            "files": raw_records,
            "schema": raw_records[0]["schema"] if raw_records else [],
            "deployment_availability": "local_raw_only",
            "target_variables": [],
            "provenance": _provenance(
                "PSI-101",
                "10.60555/2np7-jv14",
                "https://psi.nasa.gov/physci/repo/data/investigations/PSI-101",
            ),
            "experimental_conditions": PSI101_CONDITIONS,
            "limitation": "Seven local run CSVs are instrument telemetry, not independent ignition/extinction outcomes. Run 87 is outside the six-run reconciled archive.",
        },
        {
            "dataset_id": "psi101_quarantined_duplicates",
            "dataset_name": "Quarantined PSI-101 candidate CSVs",
            "dataset_group": "psi101_quarantine",
            "record_count": sum(record["record_count"] for record in quarantine_records),
            "file_count": len(quarantine_records),
            "files": quarantine_records,
            "deployment_availability": "excluded_quarantine_local_only",
            "limitation": "Both candidates are exact SHA-256 duplicates of existing Runs 95 and 97; do not count as new runs.",
        },
        {
            "dataset_id": "psi101_archived_cycle_sequence",
            "dataset_name": "PSI-101 SAME-R archived reconciled cycle sequence",
            "dataset_group": "psi101_reconciled_archive",
            "psi_id": "PSI-101",
            "source_file": archive_record["source_file"] if archive_record else None,
            "record_count": archive_record["record_count"] if archive_record else 0,
            "file_count": 1 if archive_record else 0,
            "schema": archive_record["schema"] if archive_record else [],
            "class_balance": archive_record["class_balance"] if archive_record else {},
            "run_grouping": archive_record["run_grouping"] if archive_record else {},
            "deployment_availability": "bundled_in_production",
            "target_variables": ["ExceptionIndicator", "MixedBandIndicator", "ObservedBand"],
            "provenance": _provenance(
                "PSI-101",
                "10.60555/2np7-jv14",
                "https://psi.nasa.gov/physci/repo/data/investigations/PSI-101",
            ),
            "limitation": (
                "Archived cycle labels are derived from DustTrak-A band thresholds and the historical "
                "per-run phase mapping; raw CSV replay is not performed by the deployed backend."
            ),
        },
        catalogue_record,
        *raw_records,
        *quarantine_records,
        *metadata_records,
    ]

    from src.catalogue import REPOSITORY_SCOPE

    tier2 = REPOSITORY_SCOPE.get("tier2", [])
    return {
        "registry_version": 1,
        "generated_at": date.today().isoformat(),
        "dataset_counts": {
            "tier1_catalogue_records": len(catalogue),
            "tier2_scope_records": len(tier2),
            "local_raw_run_csvs": len(raw_records),
            "local_raw_run_rows": raw_total,
            "quarantined_csvs": len(quarantine_records),
            "backend_metadata_csvs": sum(
                record["storage_scope"] == "backend_bundle" for record in metadata_records
            ),
            "workspace_metadata_csvs": sum(
                record["storage_scope"] == "workspace_derived" for record in metadata_records
            ),
            "archived_cycle_records": archive_record["record_count"] if archive_record else 0,
        },
        "datasets": datasets,
        "tier2_scope": tier2,
        "unavailable_external_raw": external,
        "other_local_artifacts": _other_local_artifacts(),
        "provenance_policy": (
            "Only files found in the current repository are reported as local. Catalogue envelopes, "
            "reconciled archive products, raw telemetry, quarantined files, and missing external raw "
            "tables are distinct evidence classes."
        ),
    }


@dataclass(frozen=True)
class TaskFeasibilityAssessment:
    task_id: str
    title: str
    candidate_task: str
    status: str
    target_definition: str
    evidence: str
    record_count: int | None
    group_count: int | None
    limitations: list[str]
    trainable_from_local_data: bool
    class_distribution: dict[str, int] | None = None
    group_ids: list[str] | None = None
    run_class_distribution: dict[str, dict[str, int]] | None = None
    grouped_split_strategy: str | None = None
    training_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "candidate_task": self.candidate_task,
            "status": self.status,
            "target_definition": self.target_definition,
            "evidence": self.evidence,
            "record_count": self.record_count,
            "group_count": self.group_count,
            "mandatory_grouping_key": "RunID" if self.group_count is not None else None,
            "limitations": self.limitations,
            "trainable_from_local_data": self.trainable_from_local_data,
            "class_distribution": self.class_distribution,
            "group_ids": self.group_ids,
            "run_class_distribution": self.run_class_distribution,
            "grouped_split_strategy": self.grouped_split_strategy,
            "training_performed": self.training_performed,
        }


def assess_candidate_tasks() -> list[dict[str, Any]]:
    from ml.datasets.loader import load_catalogue_condition_matrix, load_cycle_sequence

    model_registry_exists = (
        Path(__file__).resolve().parents[1] / "models" / "artifacts" / "registry.json"
    ).is_file()
    cycles = load_cycle_sequence()
    labelled_cycles = [
        row
        for row in cycles
        if row.get("ExceptionIndicator") in {"0", "1"}
        and row.get("MixedBandIndicator") == "0"
    ]
    positives = sum(row["ExceptionIndicator"] == "1" for row in labelled_cycles)
    negatives = sum(row["ExceptionIndicator"] == "0" for row in labelled_cycles)
    groups = sorted({row["RunID"] for row in labelled_cycles}, key=int)
    run_class_distribution: dict[str, dict[str, int]] = {}
    for row in labelled_cycles:
        counts = run_class_distribution.setdefault(row["RunID"], {"0": 0, "1": 0})
        counts[row["ExceptionIndicator"]] += 1
    catalogue = load_catalogue_condition_matrix()
    rows = len(labelled_cycles)
    assessments = [
        TaskFeasibilityAssessment(
            "task_1_combustion_outcome",
            "Combustion outcome classification",
            "Combustion outcome classification.",
            "NOT_TRAINABLE_FROM_LOCAL_RAW_DATA",
            "Independent multi-material ignition/combustion outcome per experimental trial.",
            "The local PSI-101 CSVs are smoke-aerosol detector/instrument telemetry and do not provide such outcome labels.",
            None,
            None,
            ["No local per-test ignition/no-ignition outcome matrix.", "PSI investigation envelopes are not row-level targets."],
            False,
        ),
        TaskFeasibilityAssessment(
            "task_2_extinction_sustained",
            "Flame extinction versus sustained combustion",
            "Flame extinction versus sustained combustion.",
            "NOT_TRAINABLE_FROM_LOCAL_RAW_DATA",
            "Per-test flame extinction or sustained-combustion outcome.",
            "BASS-II/FLEX are represented by catalogue-level descriptions and envelopes; no local trial table was found.",
            None,
            None,
            ["No locally downloaded BASS-II/FLEX raw extinction trial table.", "Envelope boundaries are not labeled trial rows."],
            False,
        ),
        TaskFeasibilityAssessment(
            "task_3_ignition_outcome",
            "Ignition outcome classification",
            "Ignition outcome classification.",
            "NOT_TRAINABLE_FROM_LOCAL_RAW_DATA",
            "Per-sample ignition success/failure outcome.",
            "SAFFIRE and BRE are catalogue-level in this repository; no per-sample ignition outcome table was found.",
            None,
            None,
            ["No locally downloaded SAFFIRE or BRE per-sample ignition table."],
            False,
        ),
        TaskFeasibilityAssessment(
            "task_4_flame_spread_regression",
            "Flame-spread or burning-rate regression",
            "Flame-spread or burning-rate regression.",
            "NOT_TRAINABLE_FROM_LOCAL_RAW_DATA",
            "Measured flame spread rate or burning rate tied to experimental conditions.",
            "The simulator flame-spread quantity is a code-defined surrogate, not a measured training target.",
            None,
            None,
            ["Do not train against visualization surrogates as if they were measured outcomes.", "No local multi-material rate table was found."],
            False,
        ),
        TaskFeasibilityAssessment(
            "task_5_condition_similarity",
            "Experimental condition similarity / regime profiling",
            "Experimental condition similarity.",
            "FEASIBLE_EXPLORATORY",
            "Distance or unsupervised regime profiles over catalogue condition envelopes and archived run summaries.",
            f"{len(catalogue)} catalogue investigation envelopes and six archived PSI-101 run summaries are locally available.",
            len(catalogue),
            len(catalogue),
            ["Small-N descriptive analysis only.", "Catalogued envelope values are not per-test rows.", "No clustering or model training is performed in Phase 2."],
            False,
        ),
        TaskFeasibilityAssessment(
            "task_6_psi101_archived_band_exception",
            "Smoke or aerosol experimental classification / PSI-101 phase-exception detection",
            "Smoke or aerosol experimental classification, if suitable labelled data exists.",
            "FEASIBLE_SUPERVISED_GROUPED_BY_RUN",
            "Exploratory classification of archived DustTrak-A ObservedBand and/or ExceptionIndicator labels; not fire, ignition, extinction, or smoke-versus-dust ground truth.",
            (
                f"The bundled reconciled cycle ledger has {rows:,} non-mixed labeled cycles "
                f"({negatives:,} non-exceptions, {positives:,} exceptions) across {len(groups)} RunID groups."
            ),
            rows,
            len(groups),
            [
                "Labels are derived from DustTrak-A band thresholds and a historical per-run phase mapping.",
                "Exclude ExpectedBand, ObservedBand, RelativeCyclePhase, ExceptionIndicator, MixedBandIndicator, and duplicate flags from predictors when predicting a label derived from them.",
                "Use LeaveOneGroupOut or grouped folds; report the 4, 1, 1 train/validation/test group split as a small exploratory holdout only.",
                "Raw telemetry is local-only; its seven runs have no independent aerosol/thermal regime target table.",
                "Any trained model predicts only the archived band label, not a fire, smoke, ignition, or extinction outcome.",
                "Model artifacts derived from raw PSI-101 data remain local pending redistribution-rights review.",
            ],
            True,
            class_distribution={"0": negatives, "1": positives},
            group_ids=groups,
            run_class_distribution=run_class_distribution,
            grouped_split_strategy="LeaveOneGroupOut or GroupKFold with RunID held out as a whole experiment.",
            training_performed=model_registry_exists,
        ),
    ]
    return [assessment.to_dict() for assessment in assessments]


def get_dataset_quality(dataset_id: str) -> dict[str, Any] | None:
    """Return file-specific quality and, when possible, a deterministic grouped-split audit."""
    from ml.datasets.loader import (
        load_catalogue_condition_matrix,
        load_cycle_sequence,
        load_file_by_relative_path,
        load_psi101_raw_run,
        load_psi101_raw_runs,
    )
    from ml.preprocessing.pipeline import GroupedExperimentSplit

    registry = build_dataset_registry()
    dataset = next(
        (item for item in registry["datasets"] if item.get("dataset_id") == dataset_id),
        None,
    )
    if dataset is None:
        return None

    if dataset_id == "psi101_raw_telemetry":
        rows = load_psi101_raw_runs()
    elif dataset_id == "psi101_archived_cycle_sequence":
        rows = load_cycle_sequence()
    elif dataset_id == "psi_catalogue_tier1_conditions":
        rows = load_catalogue_condition_matrix()
    elif dataset_id.startswith("psi101_raw_run_"):
        rows = load_psi101_raw_run(dataset_id.rsplit("_", 1)[-1])
    elif dataset_id.startswith("psi101_quarantine_"):
        source_file = dataset.get("source_file")
        rows = load_file_by_relative_path(source_file) if source_file else []
    else:
        source_file = dataset.get("source_file")
        if not source_file:
            return {
                "dataset_id": dataset_id,
                "dataset_name": dataset.get("dataset_name"),
                "quality_status": "no_tabular_rows",
                "record_count": dataset.get("record_count", 0),
                "limitation": dataset.get("limitation"),
            }
        rows = load_file_by_relative_path(source_file)

    normalized_rows = [dict(row) for row in rows]
    group_column = "psi_id" if dataset_id == "psi_catalogue_tier1_conditions" else "RunID"
    if normalized_rows and group_column == "RunID" and "RunID" not in normalized_rows[0]:
        for row in normalized_rows:
            source_run = row.get("Run") or row.get("run_id")
            if source_run:
                row["RunID"] = str(source_run).strip()

    fields = sorted(
        {
            field
            for row in normalized_rows
            for field in row
            if not field.startswith("_")
        }
    )
    missing_value_stats = {}
    for field in fields:
        blank = sum(
            row.get(field) is None
            or str(row.get(field)).strip().lower() in _MISSING_TEXT
            for row in normalized_rows
        )
        sentinel = sum(_is_sentinel(str(row.get(field))) for row in normalized_rows)
        if blank or sentinel:
            missing_value_stats[field] = {
                "blank_count": blank,
                "sentinel_count": sentinel,
                "missing_count": blank + sentinel,
                "missing_pct": round(
                    100 * (blank + sentinel) / len(normalized_rows), 4
                )
                if normalized_rows
                else None,
            }

    group_ids = sorted(
        {
            str(row[group_column]).strip()
            for row in normalized_rows
            if row.get(group_column)
        },
        key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value),
    )
    target_column = (
        "ExceptionIndicator"
        if normalized_rows and "ExceptionIndicator" in normalized_rows[0]
        else None
    )
    leakage_excluded_fields = sorted(_TARGET_FIELDS) if target_column else []
    safe_features = [
        field
        for field in fields
        if field != group_column
        and field != target_column
        and not field.startswith("_")
        and field not in _TARGET_FIELDS
    ]
    per_group = []
    for group_id in group_ids:
        group_rows = [
            row
            for row in normalized_rows
            if str(row.get(group_column, "")).strip() == group_id
        ]
        distribution: Counter[str] = Counter()
        if target_column:
            distribution.update(
                str(row[target_column]).strip()
                for row in group_rows
                if not _is_missing(str(row.get(target_column, "")))
            )
        per_group.append(
            {
                group_column: group_id,
                "record_count": len(group_rows),
                "target_column": target_column,
                "class_distribution": dict(sorted(distribution.items())),
            }
        )

    grouped_audit = None
    if len(group_ids) >= 3:
        result = GroupedExperimentSplit(group_col=group_column).split(
            normalized_rows,
            target_col=target_column,
            feature_columns=safe_features,
        )
        grouped_audit = result.report
    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset.get("dataset_name"),
        "source_file": dataset.get("source_file"),
        "quality_status": "inspected",
        "record_count": len(normalized_rows),
        "column_count": len(fields),
        "grouping": {
            "group_column": group_column if group_ids else None,
            "group_ids": group_ids,
            "group_count": len(group_ids),
        },
        "per_group_counts_and_class_balance": per_group,
        "target_column": target_column,
        "leakage_excluded_fields": leakage_excluded_fields,
        "class_distribution": (
            dict(sorted(Counter(
                str(row[target_column]).strip()
                for row in normalized_rows
                if not _is_missing(str(row.get(target_column, "")))
            ).items()))
            if target_column
            else {}
        ),
        "missing_value_stats": missing_value_stats,
        "grouped_split_audit": grouped_audit,
        "limitation": dataset.get("limitation"),
    }
