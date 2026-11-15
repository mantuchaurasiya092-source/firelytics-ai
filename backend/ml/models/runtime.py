from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence


MODEL_ROOT = Path(__file__).resolve().parent
ARTIFACT_ROOT = MODEL_ROOT / "artifacts"
REGISTRY_PATH = ARTIFACT_ROOT / "registry.json"


@lru_cache(maxsize=1)
def load_model_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        raise FileNotFoundError(
            "The local ML registry is missing at "
            "`backend/ml/models/artifacts/registry.json`. Model JSON files are "
            "git-ignored pending PSI-101 file-rights review, so Git-based deployments "
            "do not include them. For authorized local training, install the optional "
            "`.[ml]` extra and run `python -m ml.training.trainer` from `backend/` "
            "with the PSI-101 raw files present. Model artifacts are not generated "
            "automatically by the API."
        )
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read the local ML registry: {exc}") from exc
    if not isinstance(registry, dict) or not isinstance(registry.get("models"), list):
        raise ValueError("The local ML registry has an invalid structure.")
    return registry


def _model_entry(model_id: str) -> dict[str, Any]:
    registry = load_model_registry()
    for model in registry["models"]:
        if model.get("model_id") == model_id:
            return model
    raise KeyError(f"Unknown trained model: {model_id}")


@lru_cache(maxsize=8)
def load_model_artifact(model_id: str) -> dict[str, Any]:
    entry = _model_entry(model_id)
    relative_path = entry.get("artifact_path")
    if not isinstance(relative_path, str) or Path(relative_path).name != relative_path:
        raise ValueError(f"Model {model_id!r} has an invalid artifact path.")
    path = ARTIFACT_ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Model artifact is missing for {model_id!r}.")
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read model artifact {relative_path}: {exc}") from exc
    if artifact.get("model_id") != model_id or artifact.get("artifact_format") != "firelytics-safe-json-v1":
        raise ValueError(f"Model artifact {relative_path} failed its identity or format check.")
    return artifact


def _validated_feature_vector(
    artifact: Mapping[str, Any], features: Mapping[str, Any]
) -> tuple[list[float], list[str]]:
    names = artifact.get("feature_names")
    preprocessing = artifact.get("preprocessing")
    if not isinstance(names, list) or not isinstance(preprocessing, dict):
        raise ValueError("Model artifact is missing its feature schema or preprocessing state.")
    unknown = set(features) - set(names)
    if unknown:
        raise ValueError(f"Unknown model features: {', '.join(sorted(unknown))}.")
    medians = preprocessing.get("imputation_medians")
    if not isinstance(medians, list) or len(medians) != len(names):
        raise ValueError("Model artifact has an invalid imputation schema.")

    vector = []
    imputed = []
    for index, name in enumerate(names):
        value = features.get(name)
        if value is None:
            value = medians[index]
            imputed.append(name)
            if value is None:
                raise ValueError(f"No training median is available for missing feature {name!r}.")
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Feature {name!r} must be a finite number or null.") from exc
        if not math.isfinite(numeric_value):
            raise ValueError(f"Feature {name!r} must be finite.")
        if numeric_value == -999:
            value = medians[index]
            if value is None:
                raise ValueError(f"No training median is available for missing feature {name!r}.")
            numeric_value = float(value)
            if name not in imputed:
                imputed.append(name)
        vector.append(numeric_value)
    return vector, imputed


def _scaled_vector(vector: Sequence[float], preprocessing: Mapping[str, Any]) -> list[float]:
    scaler = preprocessing.get("standard_scaler")
    if scaler is None:
        return list(vector)
    means = scaler.get("means")
    scales = scaler.get("scales")
    if not isinstance(means, list) or not isinstance(scales, list):
        raise ValueError("Model artifact has an invalid scaler.")
    if len(means) != len(vector) or len(scales) != len(vector):
        raise ValueError("Model scaler dimensions do not match its feature schema.")
    return [(value - mean) / scale for value, mean, scale in zip(vector, means, scales)]


def _tree_leaf_value(tree: Mapping[str, Any], vector: Sequence[float]) -> list[float] | float:
    children_left = tree["children_left"]
    children_right = tree["children_right"]
    features = tree["features"]
    thresholds = tree["thresholds"]
    values = tree["values"]
    node = 0
    while children_left[node] != -1:
        feature_index = features[node]
        node = (
            children_left[node]
            if vector[feature_index] <= thresholds[node]
            else children_right[node]
        )
    return values[node]


def predict_positive_probability(
    artifact: Mapping[str, Any], features: Mapping[str, Any]
) -> tuple[float, list[str]]:
    vector, imputed = _validated_feature_vector(artifact, features)
    preprocessing = artifact["preprocessing"]
    estimator = artifact.get("estimator")
    if not isinstance(estimator, dict):
        raise ValueError("Model artifact has no supported estimator.")
    kind = estimator.get("kind")

    if kind == "logistic_regression":
        scaled = _scaled_vector(vector, preprocessing)
        score = float(estimator["intercept"]) + sum(
            weight * value for weight, value in zip(estimator["coefficients"], scaled)
        )
        probability = 1 / (1 + math.exp(-score)) if score >= 0 else math.exp(score) / (1 + math.exp(score))
    elif kind == "random_forest":
        tree_probabilities = []
        for tree in estimator["trees"]:
            leaf = _tree_leaf_value(tree, vector)
            if not isinstance(leaf, list) or len(leaf) != 2 or sum(leaf) <= 0:
                raise ValueError("Random forest artifact contains an invalid leaf value.")
            tree_probabilities.append(leaf[1] / sum(leaf))
        if not tree_probabilities:
            raise ValueError("Random forest artifact contains no trees.")
        probability = sum(tree_probabilities) / len(tree_probabilities)
    elif kind == "gradient_boosting":
        score = float(estimator["initial_log_odds"])
        for tree in estimator["trees"]:
            leaf = _tree_leaf_value(tree, vector)
            if not isinstance(leaf, (int, float)):
                raise ValueError("Gradient boosting artifact contains an invalid leaf value.")
            score += float(estimator["learning_rate"]) * float(leaf)
        probability = 1 / (1 + math.exp(-score)) if score >= 0 else math.exp(score) / (1 + math.exp(score))
    else:
        raise ValueError(f"Unsupported serialized estimator type: {kind!r}.")

    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Model produced a non-finite probability.")
    return probability, imputed


def predict_with_artifact(
    artifact: Mapping[str, Any], features: Mapping[str, Any]
) -> dict[str, Any]:
    probability, imputed = predict_positive_probability(artifact, features)
    threshold = float(artifact.get("decision_threshold", 0.5))
    predicted_class = int(probability >= threshold)
    confidence = max(probability, 1 - probability)
    entropy = 0.0
    for class_probability in (probability, 1 - probability):
        if class_probability > 0:
            entropy -= class_probability * math.log(class_probability, 2)

    class_names = artifact.get("class_names")
    if not isinstance(class_names, dict):
        raise ValueError("Model artifact is missing its target class names.")
    return {
        "predicted_class": class_names[str(predicted_class)],
        "predicted_class_id": predicted_class,
        "class_probabilities": {
            class_names["0"]: round(1 - probability, 6),
            class_names["1"]: round(probability, 6),
        },
        "confidence": round(confidence, 6),
        "confidence_pct": round(confidence * 100, 2),
        "predictive_entropy_bits": round(entropy, 6),
        "uncertainty_interpretation": (
            "Model probability and entropy are exploratory scores; probabilities are not "
            "calibrated confidence intervals or safety probabilities."
        ),
        "imputed_features": imputed,
        "target_interpretation": artifact.get("target_interpretation"),
        "safety_disclaimer": artifact.get("safety_disclaimer"),
    }
