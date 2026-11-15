from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


_MISSING_VALUES = {"", "na", "n/a", "nan", "null", "none", "-999", "-999.0"}


def numeric_or_missing(value: Any) -> float | None:
    if value is None or str(value).strip().lower() in _MISSING_VALUES:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _is_missing(value: Any) -> bool:
    return numeric_or_missing(value) is None if isinstance(value, (int, float)) else (
        value is None or str(value).strip().lower() in _MISSING_VALUES
    )


def _class_distribution(rows: Sequence[Mapping[str, Any]], target_col: str | None) -> dict[str, int]:
    if target_col is None:
        return {}
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(target_col)
        if _is_missing(value):
            continue
        key = str(value).strip()
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _imbalance_ratio(distribution: Mapping[str, int]) -> float | None:
    counts = [count for count in distribution.values() if count > 0]
    if len(counts) < 2:
        return None
    return round(max(counts) / min(counts), 6)


def _feature_missingness(
    rows: Sequence[Mapping[str, Any]],
    group_col: str,
    target_col: str | None,
    feature_columns: Sequence[str] | None,
) -> dict[str, dict[str, float | int]]:
    if not rows:
        return {}
    if feature_columns is None:
        fields = sorted(
            {
                name
                for row in rows
                for name in row
                if name != group_col
                and name != target_col
                and not name.startswith("_")
            }
        )
    else:
        fields = list(feature_columns)
    result = {}
    for field in fields:
        missing = sum(_is_missing(row.get(field)) for row in rows)
        result[field] = {
            "missing_count": missing,
            "missing_pct": round(100 * missing / len(rows), 4),
        }
    return result


def _group_map(rows: Sequence[Mapping[str, Any]], group_col: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        value = row.get(group_col)
        if value is None or not str(value).strip():
            raise ValueError(f"Every row must have a non-empty {group_col}.")
        groups.setdefault(str(value).strip(), []).append(dict(row))
    return groups


def _partition_report(
    train: Sequence[Mapping[str, Any]],
    validation: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]],
    group_col: str,
    target_col: str | None,
    feature_columns: Sequence[str] | None,
) -> dict[str, Any]:
    group_sets = {
        "train": {str(row[group_col]).strip() for row in train},
        "validation": {str(row[group_col]).strip() for row in validation},
        "test": {str(row[group_col]).strip() for row in test},
    }
    overlaps = {
        "train_validation": sorted(group_sets["train"] & group_sets["validation"]),
        "train_test": sorted(group_sets["train"] & group_sets["test"]),
        "validation_test": sorted(group_sets["validation"] & group_sets["test"]),
    }
    leakage_passed = all(not overlap for overlap in overlaps.values())
    partitions = {}
    for name, rows in (
        ("train", train),
        ("validation", validation),
        ("test", test),
    ):
        distribution = _class_distribution(rows, target_col)
        partitions[name] = {
            "row_count": len(rows),
            "run_ids": sorted(group_sets[name]),
            "group_count": len(group_sets[name]),
            "class_distribution": distribution,
            "class_imbalance_ratio": _imbalance_ratio(distribution),
            "feature_missingness": _feature_missingness(
                rows, group_col, target_col, feature_columns
            ),
        }
    return {
        "group_column": group_col,
        "target_column": target_col,
        "group_overlap": overlaps,
        "leakage_check_passed": leakage_passed,
        "partitions": partitions,
    }


@dataclass(frozen=True)
class GroupedSplit:
    train: list[dict[str, Any]]
    validation: list[dict[str, Any]]
    test: list[dict[str, Any]]
    report: dict[str, Any]


class GroupedExperimentSplit:
    """Deterministic three-way split that assigns entire experiments to one partition."""

    def __init__(
        self,
        group_col: str = "RunID",
        test_size: float = 0.2,
        validation_size: float = 0.2,
        random_state: int = 42,
    ) -> None:
        if not 0 < test_size < 1 or not 0 < validation_size < 1:
            raise ValueError("test_size and validation_size must be between 0 and 1.")
        if test_size + validation_size >= 1:
            raise ValueError("test_size plus validation_size must leave training data.")
        self.group_col = group_col
        self.test_size = test_size
        self.validation_size = validation_size
        self.random_state = random_state

    def split(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        target_col: str | None = None,
        feature_columns: Sequence[str] | None = None,
    ) -> GroupedSplit:
        records = [dict(row) for row in rows]
        groups = _group_map(records, self.group_col)
        group_ids = sorted(groups)
        if len(group_ids) < 3:
            raise ValueError("At least three distinct experiment groups are required for train/validation/test.")

        shuffled = list(group_ids)
        random.Random(self.random_state).shuffle(shuffled)
        test_count = max(1, round(len(shuffled) * self.test_size))
        validation_count = max(1, round(len(shuffled) * self.validation_size))
        while test_count + validation_count >= len(shuffled):
            if test_count >= validation_count and test_count > 1:
                test_count -= 1
            elif validation_count > 1:
                validation_count -= 1
            else:
                raise ValueError("Not enough distinct groups for non-empty train/validation/test partitions.")

        test_ids = set(shuffled[:test_count])
        validation_ids = set(shuffled[test_count : test_count + validation_count])
        train_ids = set(shuffled[test_count + validation_count :])
        train = [row for group in sorted(train_ids) for row in groups[group]]
        validation = [row for group in sorted(validation_ids) for row in groups[group]]
        test = [row for group in sorted(test_ids) for row in groups[group]]
        report = _partition_report(
            train, validation, test, self.group_col, target_col, feature_columns
        )
        if not report["leakage_check_passed"]:
            raise RuntimeError("Grouped split produced overlapping experiment IDs.")
        return GroupedSplit(train, validation, test, report)

    def group_k_fold(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        n_splits: int = 5,
        target_col: str | None = None,
        feature_columns: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        records = [dict(row) for row in rows]
        groups = _group_map(records, self.group_col)
        if not 2 <= n_splits <= len(groups):
            raise ValueError("n_splits must be between 2 and the number of unique groups.")
        fold_groups: list[list[str]] = [[] for _ in range(n_splits)]
        fold_rows = [0] * n_splits
        ordered = sorted(groups, key=lambda group: (-len(groups[group]), group))
        for group in ordered:
            fold = min(range(n_splits), key=lambda index: (fold_rows[index], len(fold_groups[index]), index))
            fold_groups[fold].append(group)
            fold_rows[fold] += len(groups[group])

        folds = []
        all_ids = set(groups)
        for fold_index, test_ids_list in enumerate(fold_groups):
            test_ids = set(test_ids_list)
            train = [row for group in sorted(all_ids - test_ids) for row in groups[group]]
            test = [row for group in sorted(test_ids) for row in groups[group]]
            report = _partition_report(
                train, [], test, self.group_col, target_col, feature_columns
            )
            if not report["leakage_check_passed"]:
                raise RuntimeError(f"GroupKFold fold {fold_index} has group leakage.")
            folds.append(
                {
                    "fold": fold_index,
                    "train": train,
                    "test": test,
                    "report": report,
                }
            )
        return folds

    def leave_one_group_out(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        target_col: str | None = None,
        feature_columns: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        records = [dict(row) for row in rows]
        groups = _group_map(records, self.group_col)
        return self.group_k_fold(
            records,
            n_splits=len(groups),
            target_col=target_col,
            feature_columns=feature_columns,
        )


def fit_median_imputer(
    rows: Sequence[Mapping[str, Any]], feature_columns: Sequence[str]
) -> dict[str, float | None]:
    """Fit numeric medians from training rows only; missing/sentinel cells are ignored."""
    medians: dict[str, float | None] = {}
    for column in feature_columns:
        values = sorted(
            parsed
            for row in rows
            if (parsed := numeric_or_missing(row.get(column))) is not None
        )
        medians[column] = statistics.median(values) if values else None
    return medians


def apply_median_imputer(
    rows: Sequence[Mapping[str, Any]], medians: Mapping[str, float | None]
) -> list[dict[str, Any]]:
    """Replace missing or -999 numeric cells using training-only fitted medians."""
    result = []
    for row in rows:
        transformed = dict(row)
        for column, median in medians.items():
            if _is_missing(transformed.get(column)) and median is not None:
                transformed[column] = median
        result.append(transformed)
    return result


class UnitAwareStandardScaler:
    """Standardize numeric features while requiring one declared unit per feature."""

    def __init__(self) -> None:
        self.units: dict[str, str] = {}
        self.means: dict[str, float] = {}
        self.scales: dict[str, float] = {}
        self._fitted = False

    def fit(
        self,
        rows: Sequence[Mapping[str, Any]],
        feature_units: Mapping[str, str],
    ) -> UnitAwareStandardScaler:
        if not rows:
            raise ValueError("Cannot fit a scaler on an empty training partition.")
        if not feature_units or any(not unit.strip() for unit in feature_units.values()):
            raise ValueError("Every scaled feature must have an explicit unit.")
        self.units = dict(feature_units)
        for column in self.units:
            values = [
                parsed
                for row in rows
                if (parsed := numeric_or_missing(row.get(column))) is not None
            ]
            if not values:
                raise ValueError(f"Training feature {column!r} has no usable numeric values.")
            mean = statistics.fmean(values)
            scale = statistics.pstdev(values)
            self.means[column] = mean
            self.scales[column] = scale if scale > 0 else 1.0
        self._fitted = True
        return self

    def transform(
        self,
        rows: Sequence[Mapping[str, Any]],
        feature_units: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        if not self._fitted:
            raise RuntimeError("Fit the scaler using training data before transforming.")
        if dict(feature_units) != self.units:
            raise ValueError("Feature units differ from the units used when fitting the scaler.")
        result = []
        for row in rows:
            transformed = dict(row)
            for column in self.units:
                value = numeric_or_missing(row.get(column))
                transformed[column] = (
                    (value - self.means[column]) / self.scales[column]
                    if value is not None
                    else None
                )
            result.append(transformed)
        return result

    def metadata(self) -> dict[str, Any]:
        if not self._fitted:
            raise RuntimeError("Scaler metadata is unavailable before fitting.")
        return {
            column: {
                "unit": self.units[column],
                "training_mean": self.means[column],
                "training_scale": self.scales[column],
            }
            for column in self.units
        }
