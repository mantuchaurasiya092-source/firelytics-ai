from __future__ import annotations

import math
import random
from itertools import combinations
from typing import Any, Callable, Sequence


def exact_interventional_shap_summary(
    predict_positive_probability: Callable[[Sequence[Sequence[float | None]]], Sequence[float]],
    rows: Sequence[Sequence[float | None]],
    feature_names: Sequence[str],
    feature_units: dict[str, str],
    *,
    background_size: int = 32,
    explained_size: int = 64,
    random_state: int = 42,
) -> dict[str, Any]:
    """Compute exact empirical interventional Shapley values for a small feature set."""
    feature_count = len(feature_names)
    if feature_count == 0 or feature_count > 8:
        raise ValueError("Exact Shapley enumeration requires between 1 and 8 features.")
    if not rows:
        raise ValueError("At least one row is required for explainability.")
    if any(len(row) != feature_count for row in rows):
        raise ValueError("Every explanation row must match the declared feature schema.")
    if set(feature_names) != set(feature_units):
        raise ValueError("Each explanation feature must have exactly one declared unit.")

    rng = random.Random(random_state)
    indices = list(range(len(rows)))
    background_indices = sorted(rng.sample(indices, min(background_size, len(indices))))
    explained_indices = sorted(rng.sample(indices, min(explained_size, len(indices))))
    background = [list(rows[index]) for index in background_indices]
    explained = [list(rows[index]) for index in explained_indices]
    coalition_values: dict[int, list[float]] = {}
    full_mask = (1 << feature_count) - 1

    for coalition_mask in range(full_mask + 1):
        hybrid_rows = []
        for explained_row in explained:
            for background_row in background:
                hybrid_rows.append(
                    [
                        explained_row[feature_index]
                        if coalition_mask & (1 << feature_index)
                        else background_row[feature_index]
                        for feature_index in range(feature_count)
                    ]
                )
        probabilities = list(predict_positive_probability(hybrid_rows))
        if len(probabilities) != len(hybrid_rows):
            raise ValueError("The model returned an unexpected number of explanation scores.")
        coalition_values[coalition_mask] = [
            sum(probabilities[offset : offset + len(background)]) / len(background)
            for offset in range(0, len(probabilities), len(background))
        ]

    factorial = math.factorial
    denominator = factorial(feature_count)
    shap_values = [[0.0] * feature_count for _ in explained]
    for feature_index in range(feature_count):
        feature_mask = 1 << feature_index
        other_features = [index for index in range(feature_count) if index != feature_index]
        for coalition_size in range(feature_count):
            weight = (
                factorial(coalition_size)
                * factorial(feature_count - coalition_size - 1)
                / denominator
            )
            for coalition in combinations(other_features, coalition_size):
                coalition_mask = sum(1 << index for index in coalition)
                before = coalition_values[coalition_mask]
                after = coalition_values[coalition_mask | feature_mask]
                for row_index, (before_value, after_value) in enumerate(zip(before, after)):
                    shap_values[row_index][feature_index] += weight * (after_value - before_value)

    summaries = []
    for feature_index, feature_name in enumerate(feature_names):
        contributions = [values[feature_index] for values in shap_values]
        summaries.append(
            {
                "feature": feature_name,
                "unit": feature_units[feature_name],
                "mean_abs_shap": sum(abs(value) for value in contributions) / len(contributions),
                "mean_shap": sum(contributions) / len(contributions),
            }
        )
    summaries.sort(key=lambda item: (-item["mean_abs_shap"], item["feature"]))
    for rank, summary in enumerate(summaries, start=1):
        summary["rank"] = rank
        summary["mean_abs_shap"] = round(summary["mean_abs_shap"], 8)
        summary["mean_shap"] = round(summary["mean_shap"], 8)

    return {
        "method": "Exact interventional Shapley values over a deterministic empirical background sample.",
        "explained_output": "Predicted probability of the archived DustTrak-A ObservedBand class '20000+'.",
        "background_sample_count": len(background),
        "explained_sample_count": len(explained),
        "feature_count": feature_count,
        "data_scope": "Training rows from six PSI-101 runs; global descriptive summary, not a held-out explanation.",
        "summary": summaries,
    }
