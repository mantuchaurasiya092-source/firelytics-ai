from __future__ import annotations

import json
import hashlib
import math
import statistics
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ml.datasets.loader import load_cycle_sequence, load_psi101_raw_runs
from ml.datasets.registry import ARCHIVE_CYCLE_FILE, RAW_PYRELL_ROOT, ROOT
from ml.evaluation.metrics import classification_metrics
from ml.explainability.explainer import exact_interventional_shap_summary
from ml.models.runtime import ARTIFACT_ROOT, predict_positive_probability
from ml.preprocessing.pipeline import GroupedExperimentSplit, numeric_or_missing


MODEL_VERSION = "1.0.0"
CLASS_NAMES = {"0": "10000-14999", "1": "20000+"}
TARGET_INTERPRETATION = (
    "Archived PSI-101 DustTrak-A ObservedBand category only. This is not a fire, ignition, "
    "flame-extinction, smoke-versus-dust, or nuisance-dust outcome."
)
SAFETY_DISCLAIMER = (
    "Exploratory research surrogate trained on archived PSI-101 aerosol-band labels; "
    "not a fire prediction, spacecraft safety assessment, calibrated probability, "
    "control instruction, or NASA-approved result."
)
FEATURE_DEFINITIONS = (
    {
        "name": "dusttrak_b_mass_mg_m3",
        "source_column": "DustTrakBMeasurement(MgPerM3)",
        "label": "DustTrak B mass concentration",
        "unit": "mg/m³",
    },
    {
        "name": "ptrak_particles_cm3",
        "source_column": "PTrakMeasurement(PtPerCC)",
        "label": "P-Trak particle number concentration",
        "unit": "particles/cm³",
    },
    {
        "name": "gas_plume_temp_c",
        "source_column": "GasPlumeTemperature(DegC)",
        "label": "Gas plume temperature",
        "unit": "°C",
    },
    {
        "name": "sample_resistance_ohms",
        "source_column": "SampleResistance(Ohms)",
        "label": "Sample heater resistance",
        "unit": "Ω",
    },
    {
        "name": "mfc_mass_flow_lpm",
        "source_column": "MFCMassFlowRate(LPM)",
        "label": "MFC mass flow rate",
        "unit": "L/min",
    },
)
FEATURE_NAMES = [item["name"] for item in FEATURE_DEFINITIONS]
FEATURE_UNITS = {item["name"]: item["unit"] for item in FEATURE_DEFINITIONS}
FEATURE_LABELS = {item["name"]: item["label"] for item in FEATURE_DEFINITIONS}
ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)


def build_training_dataset() -> list[dict[str, Any]]:
    """Align the bundled cycle labels to local raw channels using archived row references."""
    cycles = load_cycle_sequence()
    run_ids = sorted({row["RunID"] for row in cycles}, key=int)
    raw_rows = load_psi101_raw_runs(run_ids)
    raw_by_source_row: dict[tuple[str, int], Mapping[str, Any]] = {}
    for row in raw_rows:
        source_row = int(row["_source_row"])
        key = (str(row["RunID"]), source_row)
        if key in raw_by_source_row:
            raise ValueError(f"Duplicate raw source-row key in PSI-101 data: {key!r}.")
        raw_by_source_row[key] = row

    training_rows = []
    for cycle in cycles:
        band = cycle["ObservedBand"]
        mixed = cycle["MixedBandIndicator"]
        if mixed not in {"0", "1"}:
            raise ValueError(f"Run {cycle['RunID']} cycle {cycle['Cycle']} has an invalid mixed-band flag.")
        if mixed == "1":
            if band != "MixedBand":
                raise ValueError(
                    f"Run {cycle['RunID']} cycle {cycle['Cycle']} has inconsistent mixed-band labels."
                )
            continue
        if band not in CLASS_NAMES.values():
            raise ValueError(
                f"Run {cycle['RunID']} cycle {cycle['Cycle']} has an unsupported ObservedBand label {band!r}."
            )
        references = [
            int(value)
            for value in cycle["SourceDataRows"].split(";")
            if value.strip()
        ]
        if not references:
            raise ValueError(
                f"Run {cycle['RunID']} cycle {cycle['Cycle']} has no source-row references."
            )
        try:
            source_rows = [raw_by_source_row[(cycle["RunID"], reference)] for reference in references]
        except KeyError as exc:
            raise ValueError(
                f"Archived row references are not present in the local PSI-101 raw files: {exc}."
            ) from exc

        features: dict[str, float | None] = {}
        for definition in FEATURE_DEFINITIONS:
            values = [
                value
                for source_row in source_rows
                if (value := numeric_or_missing(source_row.get(definition["source_column"]))) is not None
            ]
            features[definition["name"]] = statistics.median(values) if values else None
        training_rows.append(
            {
                **features,
                "RunID": cycle["RunID"],
                "target": 0 if band == CLASS_NAMES["0"] else 1,
                "_row_index": len(training_rows),
            }
        )

    if not training_rows:
        raise ValueError("No binary PSI-101 ObservedBand records are eligible for training.")
    if {row["target"] for row in training_rows} != {0, 1}:
        raise ValueError("The eligible PSI-101 target must contain both archived band classes.")
    if len({row["RunID"] for row in training_rows}) < 3:
        raise ValueError("At least three distinct PSI-101 RunID groups are required.")
    return training_rows


def _numeric_matrix(rows: Sequence[Mapping[str, Any]], numpy: Any) -> Any:
    return numpy.asarray(
        [
            [
                float(value) if value is not None and math.isfinite(float(value)) else numpy.nan
                for value in (row.get(name) for name in FEATURE_NAMES)
            ]
            for row in rows
        ],
        dtype=float,
    )


def _new_estimator(model_id: str) -> Any:
    try:
        from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError(
            "Training requires the optional ML extra. Install it with "
            "`python -m pip install -e \".[ml]\"` from the backend directory."
        ) from exc

    steps = [("imputer", SimpleImputer(strategy="median", keep_empty_features=True))]
    if model_id == "logistic_regression":
        steps.append(("scaler", StandardScaler()))
        classifier = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=42)
    elif model_id == "random_forest":
        classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=1,
        )
    elif model_id == "gradient_boosting":
        classifier = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=2,
            min_samples_leaf=5,
            random_state=42,
        )
    else:
        raise ValueError(f"Unsupported baseline model ID: {model_id!r}.")
    steps.append(("classifier", classifier))
    return Pipeline(steps)


def _tree_data(tree_estimator: Any, *, classification: bool) -> dict[str, Any]:
    tree = tree_estimator.tree_
    values = []
    for node in range(tree.node_count):
        raw_values = tree.value[node][0]
        if classification:
            values.append([float(raw_values[0]), float(raw_values[1])])
        else:
            values.append(float(raw_values[0]))
    return {
        "children_left": [int(value) for value in tree.children_left],
        "children_right": [int(value) for value in tree.children_right],
        "features": [int(value) for value in tree.feature],
        "thresholds": [float(value) for value in tree.threshold],
        "values": values,
    }


def _export_pipeline(model_id: str, pipeline: Any) -> dict[str, Any]:
    classifier = pipeline.named_steps["classifier"]
    imputer = pipeline.named_steps["imputer"]
    preprocessing: dict[str, Any] = {
        "imputation_medians": [
            float(value) if math.isfinite(float(value)) else None
            for value in imputer.statistics_
        ],
        "standard_scaler": None,
    }
    if model_id == "logistic_regression":
        scaler = pipeline.named_steps["scaler"]
        preprocessing["standard_scaler"] = {
            "means": [float(value) for value in scaler.mean_],
            "scales": [float(value) for value in scaler.scale_],
        }
        estimator = {
            "kind": "logistic_regression",
            "coefficients": [float(value) for value in classifier.coef_[0]],
            "intercept": float(classifier.intercept_[0]),
        }
    elif model_id == "random_forest":
        estimator = {
            "kind": "random_forest",
            "trees": [
                _tree_data(tree, classification=True)
                for tree in classifier.estimators_
            ],
        }
    else:
        prior = classifier.init_.class_prior_
        if len(prior) != 2 or prior[0] <= 0 or prior[1] <= 0:
            raise ValueError("Gradient boosting requires non-empty binary class priors.")
        estimator = {
            "kind": "gradient_boosting",
            "initial_log_odds": math.log(float(prior[1]) / float(prior[0])),
            "learning_rate": float(classifier.learning_rate),
            "trees": [
                _tree_data(stage[0], classification=False)
                for stage in classifier.estimators_
            ],
        }
    return {"preprocessing": preprocessing, "estimator": estimator}


def _native_feature_importance(model_id: str, pipeline: Any) -> list[dict[str, Any]]:
    classifier = pipeline.named_steps["classifier"]
    if hasattr(classifier, "feature_importances_"):
        values = classifier.feature_importances_
        basis = "tree impurity reduction"
    else:
        values = abs(classifier.coef_[0])
        basis = "absolute standardized logistic coefficient"
    result = [
        {
            "feature": feature_name,
            "label": FEATURE_LABELS[feature_name],
            "unit": FEATURE_UNITS[feature_name],
            "importance": float(value),
            "importance_basis": basis,
        }
        for feature_name, value in zip(FEATURE_NAMES, values)
    ]
    return sorted(result, key=lambda item: (-item["importance"], item["feature"]))


def _training_source_paths() -> list[Path]:
    runs = ("063", "064", "076", "084", "095", "097")
    return [
        ARCHIVE_CYCLE_FILE,
        *[
            next((RAW_PYRELL_ROOT / f"Run_{run}").glob("*.csv"))
            for run in runs
        ],
    ]


def _source_hashes() -> dict[str, str]:
    hashes = {}
    for path in _training_source_paths():
        if not path.is_file():
            raise FileNotFoundError(f"Training source file is missing: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[path.relative_to(ROOT).as_posix()] = digest
    return hashes


def _training_parameters(model_id: str) -> dict[str, Any]:
    if model_id == "logistic_regression":
        return {"solver": "lbfgs", "max_iter": 1000, "standard_scaled": True, "random_state": 42}
    if model_id == "random_forest":
        return {
            "n_estimators": 100,
            "max_depth": 8,
            "min_samples_leaf": 5,
            "class_weight": "balanced_subsample",
            "random_state": 42,
        }
    return {
        "n_estimators": 100,
        "learning_rate": 0.05,
        "max_depth": 2,
        "min_samples_leaf": 5,
        "random_state": 42,
    }


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as handle:
        temporary_path = Path(handle.name)
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    temporary_path.replace(path)


def train_models() -> dict[str, Any]:
    """Run leave-one-RunID-out evaluation and persist portable JSON classifiers."""
    try:
        import numpy as np
        import sklearn
    except ImportError as exc:
        raise RuntimeError("Training requires scikit-learn through the optional ML extra.") from exc

    rows = build_training_dataset()
    source_hashes = _source_hashes()
    target_values = [int(row["target"]) for row in rows]
    feature_rows = _numeric_matrix(rows, np)
    run_ids = sorted({str(row["RunID"]) for row in rows}, key=int)
    splitter = GroupedExperimentSplit(group_col="RunID", random_state=42)
    folds = splitter.leave_one_group_out(
        rows,
        target_col="target",
        feature_columns=FEATURE_NAMES,
    )
    model_specs = (
        ("logistic_regression", "Logistic Regression"),
        ("random_forest", "Random Forest"),
        ("gradient_boosting", "Gradient Boosting"),
    )
    model_summaries = []
    for model_id, display_name in model_specs:
        out_of_fold_probabilities = [0.0] * len(rows)
        majority_baseline_probabilities = [0.0] * len(rows)
        out_of_fold_labels = list(target_values)
        out_of_fold_groups = [str(row["RunID"]) for row in rows]
        group_partitions = []
        for fold in folds:
            report = fold["report"]
            if not report["leakage_check_passed"]:
                raise RuntimeError("Grouped model evaluation detected RunID overlap.")
            test_runs = report["partitions"]["test"]["run_ids"]
            train_runs = report["partitions"]["train"]["run_ids"]
            if len(test_runs) != 1 or set(train_runs) & set(test_runs):
                raise RuntimeError("Leave-one-run-out fold has invalid group assignments.")
            train_rows = fold["train"]
            test_rows = fold["test"]
            estimator = _new_estimator(model_id)
            estimator.fit(_numeric_matrix(train_rows, np), [int(row["target"]) for row in train_rows])
            probabilities = estimator.predict_proba(_numeric_matrix(test_rows, np))[:, 1]
            row_indices = [int(row["_row_index"]) for row in test_rows]
            if len(row_indices) != len(test_rows):
                raise RuntimeError("Could not reconcile held-out rows to their RunID group.")
            training_class_counts = {
                target: sum(int(row["target"]) == target for row in train_rows)
                for target in (0, 1)
            }
            baseline_prediction = int(
                training_class_counts[1] > training_class_counts[0]
            )
            for row_index, probability in zip(row_indices, probabilities):
                out_of_fold_probabilities[row_index] = float(probability)
                majority_baseline_probabilities[row_index] = float(baseline_prediction)
            group_partitions.append(
                {
                    "heldout_run_ids": test_runs,
                    "training_run_ids": train_runs,
                    "training_class_distribution": {
                        str(label): count for label, count in training_class_counts.items()
                    },
                    "majority_baseline_class": baseline_prediction,
                    "leakage_check_passed": True,
                }
            )

        validation_metrics = classification_metrics(
            out_of_fold_labels, out_of_fold_probabilities
        )
        majority_baseline_metrics = classification_metrics(
            out_of_fold_labels, majority_baseline_probabilities
        )
        per_run_metrics = {}
        for run_id in run_ids:
            indices = [index for index, group in enumerate(out_of_fold_groups) if group == run_id]
            per_run_metrics[run_id] = classification_metrics(
                [out_of_fold_labels[index] for index in indices],
                [out_of_fold_probabilities[index] for index in indices],
            )

        final_pipeline = _new_estimator(model_id)
        final_pipeline.fit(feature_rows, target_values)
        exported = _export_pipeline(model_id, final_pipeline)
        artifact_path = f"{model_id}_v{MODEL_VERSION.replace('.', '_')}.json"

        def explain_probability(samples: Sequence[Sequence[float | None]]) -> list[float]:
            matrix = _numeric_matrix(
                [
                    {feature_name: value for feature_name, value in zip(FEATURE_NAMES, sample)}
                    for sample in samples
                ],
                np,
            )
            return [float(value) for value in final_pipeline.predict_proba(matrix)[:, 1]]

        explanation = exact_interventional_shap_summary(
            explain_probability,
            [
                [row.get(feature_name) for feature_name in FEATURE_NAMES]
                for row in rows
            ],
            FEATURE_NAMES,
            FEATURE_UNITS,
        )
        for item in explanation["summary"]:
            item["label"] = FEATURE_LABELS[item["feature"]]
        native_importance = _native_feature_importance(model_id, final_pipeline)

        artifact = {
            "artifact_format": "firelytics-safe-json-v1",
            "model_id": model_id,
            "model_version": MODEL_VERSION,
            "display_name": display_name,
            "algorithm": display_name,
            "training_parameters": _training_parameters(model_id),
            "dataset": "PSI-101 SAME-R Pyrell archived cycle labels joined to local raw telemetry",
            "dataset_id": "psi101_archived_cycle_sequence",
            "target_name": "ObservedBand",
            "target_interpretation": TARGET_INTERPRETATION,
            "class_names": CLASS_NAMES,
            "decision_threshold": 0.5,
            "feature_names": FEATURE_NAMES,
            "feature_schema": [
                {
                    "name": item["name"],
                    "label": item["label"],
                    "unit": item["unit"],
                    "source_column": item["source_column"],
                }
                for item in FEATURE_DEFINITIONS
            ],
            "preprocessing": exported["preprocessing"],
            "estimator": exported["estimator"],
            "validation_metrics": validation_metrics,
            "grouped_majority_baseline": majority_baseline_metrics,
            "accuracy_delta_vs_grouped_majority_baseline": round(
                validation_metrics["accuracy"] - majority_baseline_metrics["accuracy"], 6
            ),
            "per_run_metrics": per_run_metrics,
            "grouped_evaluation": {
                "method": "Leave-One-RunID-Out (grouped folds)",
                "group_column": "RunID",
                "run_ids": run_ids,
                "folds": group_partitions,
                "leakage_check_passed": all(
                    item["leakage_check_passed"] for item in group_partitions
                ),
                "out_of_fold_prediction_count": len(out_of_fold_probabilities),
            },
            "training_metadata": {
                "training_performed": True,
                "record_count": len(rows),
                "class_distribution": {
                    "0": target_values.count(0),
                    "1": target_values.count(1),
                },
                "run_group_count": len(run_ids),
                "raw_feature_data_local_only": True,
                "source_file_sha256": source_hashes,
                "runtime_versions": {
                    "python": sys.version.split()[0],
                    "numpy": np.__version__,
                    "scikit_learn": sklearn.__version__,
                },
                "label_exclusions": ["MixedBand"],
                "target_generating_measurements_excluded": [
                    "DustTrakAMeasurement(MgPerM3)",
                    "DustTrakAAnalogMeasurement(Volts)",
                ],
                "disclaimer": SAFETY_DISCLAIMER,
            },
            "feature_importance": native_importance,
            "explainability": {
                **explanation,
                "global_feature_importance": native_importance,
                "shap_summary": explanation["summary"],
            },
            "safety_disclaimer": SAFETY_DISCLAIMER,
            "artifact_policy": (
                "Local-only artifact. Raw PSI-101 file redistribution terms are not "
                "established; do not package or distribute this derived model without rights review."
            ),
        }

        parity_rows = rows[: min(20, len(rows))]
        for row in parity_rows:
            input_features = {name: row[name] for name in FEATURE_NAMES}
            runtime_probability, _ = predict_positive_probability(artifact, input_features)
            sklearn_probability = float(
                final_pipeline.predict_proba(_numeric_matrix([row], np))[0, 1]
            )
            if abs(runtime_probability - sklearn_probability) > 1e-8:
                raise RuntimeError(
                    f"Portable {model_id} inference differs from its fitted estimator."
                )

        _atomic_json_write(ARTIFACT_ROOT / artifact_path, artifact)
        model_summaries.append(
            {
                "model_id": model_id,
                "version": MODEL_VERSION,
                "display_name": display_name,
                "algorithm": display_name,
                "training_parameters": artifact["training_parameters"],
                "artifact_path": artifact_path,
                "dataset": artifact["dataset"],
                "dataset_id": artifact["dataset_id"],
                "target_name": artifact["target_name"],
                "target_interpretation": TARGET_INTERPRETATION,
                "feature_schema": artifact["feature_schema"],
                "feature_names": FEATURE_NAMES,
                "training_metadata": artifact["training_metadata"],
                "validation_metrics": validation_metrics,
                "grouped_majority_baseline": majority_baseline_metrics,
                "accuracy_delta_vs_grouped_majority_baseline": artifact[
                    "accuracy_delta_vs_grouped_majority_baseline"
                ],
                "per_run_metrics": per_run_metrics,
                "grouped_evaluation": artifact["grouped_evaluation"],
                "feature_importance": native_importance,
                "explainability": artifact["explainability"],
                "safety_disclaimer": SAFETY_DISCLAIMER,
                "artifact_policy": artifact["artifact_policy"],
            }
        )

    registry = {
        "registry_version": "1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "task_id": "task_6_psi101_archived_band_exception",
        "task_name": "PSI-101 archived DustTrak-A ObservedBand classification",
        "target_interpretation": TARGET_INTERPRETATION,
        "class_names": CLASS_NAMES,
        "training_performed": True,
        "record_count": len(rows),
        "run_ids": run_ids,
        "grouped_evaluation_method": "Leave-One-RunID-Out (grouped folds)",
        "runid_leakage_check_passed": True,
        "model_artifacts_local_only": True,
        "safety_disclaimer": SAFETY_DISCLAIMER,
        "models": model_summaries,
    }
    _atomic_json_write(ARTIFACT_ROOT / "registry.json", registry)
    return registry


def main() -> None:
    registry = train_models()
    print(
        json.dumps(
            {
                "task_id": registry["task_id"],
                "training_performed": registry["training_performed"],
                "record_count": registry["record_count"],
                "run_ids": registry["run_ids"],
                "runid_leakage_check_passed": registry["runid_leakage_check_passed"],
                "models": [
                    {
                        "model_id": model["model_id"],
                        "accuracy": model["validation_metrics"]["accuracy"],
                        "f1": model["validation_metrics"]["f1"],
                        "roc_auc": model["validation_metrics"]["roc_auc"],
                    }
                    for model in registry["models"]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
