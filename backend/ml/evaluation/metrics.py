from __future__ import annotations

import math
from typing import Any, Sequence


def _rounded(value: float | None) -> float | None:
    return round(value, 6) if value is not None and math.isfinite(value) else None


def _roc_curve(
    labels: Sequence[int], probabilities: Sequence[float]
) -> tuple[float | None, list[dict[str, float]]]:
    positives = sum(label == 1 for label in labels)
    negatives = sum(label == 0 for label in labels)
    if not positives or not negatives:
        return None, []

    ordered = sorted(zip(probabilities, labels), key=lambda item: item[0], reverse=True)
    points = [(0.0, 0.0)]
    true_positives = 0
    false_positives = 0
    index = 0
    while index < len(ordered):
        threshold = ordered[index][0]
        while index < len(ordered) and ordered[index][0] == threshold:
            if ordered[index][1] == 1:
                true_positives += 1
            else:
                false_positives += 1
            index += 1
        points.append((false_positives / negatives, true_positives / positives))

    auc = sum(
        (right[0] - left[0]) * (right[1] + left[1]) / 2
        for left, right in zip(points, points[1:])
    )
    if len(points) > 101:
        selected = {
            round(position * (len(points) - 1) / 100)
            for position in range(101)
        }
        points = [point for index, point in enumerate(points) if index in selected]
    return auc, [{"false_positive_rate": fpr, "true_positive_rate": tpr} for fpr, tpr in points]


def classification_metrics(
    labels: Sequence[int], positive_probabilities: Sequence[float], *, calibration_bins: int = 10
) -> dict[str, Any]:
    """Calculate binary metrics and calibration diagnostics from held-out predictions."""
    if len(labels) != len(positive_probabilities):
        raise ValueError("Labels and predicted probabilities must have equal lengths.")
    if not labels:
        raise ValueError("At least one held-out prediction is required.")
    if any(label not in (0, 1) for label in labels):
        raise ValueError("Binary labels must be encoded as 0 or 1.")
    if any(not math.isfinite(probability) or not 0 <= probability <= 1 for probability in positive_probabilities):
        raise ValueError("Predicted probabilities must be finite values between 0 and 1.")
    if calibration_bins < 1:
        raise ValueError("calibration_bins must be positive.")

    predictions = [int(probability >= 0.5) for probability in positive_probabilities]
    true_negative = sum(actual == 0 and predicted == 0 for actual, predicted in zip(labels, predictions))
    false_positive = sum(actual == 0 and predicted == 1 for actual, predicted in zip(labels, predictions))
    false_negative = sum(actual == 1 and predicted == 0 for actual, predicted in zip(labels, predictions))
    true_positive = sum(actual == 1 and predicted == 1 for actual, predicted in zip(labels, predictions))
    correct = true_positive + true_negative
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    brier_score = sum((probability - label) ** 2 for label, probability in zip(labels, positive_probabilities)) / len(labels)

    calibration = []
    weighted_calibration_error = 0.0
    for bin_index in range(calibration_bins):
        lower = bin_index / calibration_bins
        upper = (bin_index + 1) / calibration_bins
        in_bin = [
            (label, probability, prediction)
            for label, probability, prediction in zip(labels, positive_probabilities, predictions)
            if lower <= max(probability, 1 - probability) < upper
            or (bin_index == calibration_bins - 1 and max(probability, 1 - probability) == 1)
        ]
        if not in_bin:
            continue
        mean_confidence = sum(max(probability, 1 - probability) for _, probability, _ in in_bin) / len(in_bin)
        accuracy = sum(label == prediction for label, _, prediction in in_bin) / len(in_bin)
        weighted_calibration_error += len(in_bin) / len(labels) * abs(mean_confidence - accuracy)
        calibration.append(
            {
                "lower_bound": round(lower, 2),
                "upper_bound": round(upper, 2),
                "count": len(in_bin),
                "mean_confidence": _rounded(mean_confidence),
                "observed_accuracy": _rounded(accuracy),
            }
        )

    roc_auc, roc_points = _roc_curve(labels, positive_probabilities)
    return {
        "sample_count": len(labels),
        "class_distribution": {"0": labels.count(0), "1": labels.count(1)},
        "threshold": 0.5,
        "accuracy": _rounded(correct / len(labels)),
        "precision": _rounded(precision),
        "recall": _rounded(recall),
        "f1": _rounded(f1),
        "roc_auc": _rounded(roc_auc),
        "confusion_matrix": {
            "labels": ["10000-14999", "20000+"],
            "matrix": [[true_negative, false_positive], [false_negative, true_positive]],
        },
        "calibration": {
            "status": "diagnostic_only_not_calibration_adjusted",
            "brier_score": _rounded(brier_score),
            "expected_calibration_error": _rounded(weighted_calibration_error),
            "bins": calibration,
            "confidence_interpretation": (
                "Maximum class probability is a model score, not a statistically calibrated "
                "confidence interval."
            ),
        },
        "roc_curve": roc_points,
    }
