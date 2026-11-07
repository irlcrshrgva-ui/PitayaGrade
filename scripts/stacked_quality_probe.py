"""Validation-select a score stacker for the retained quality classifiers.

The stacker is trained and selected only inside stratified folds of the
validation split. The reused test split is evaluated once after selection.
This remains development evidence, not a fresh field-accuracy estimate.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from scripts.ensemble_quality_probe import infer, metrics, parse_model, sha256
from scripts.reviewed_training import read_reviewed_manifest


def feature_view(scores, view):
    """Flatten model probabilities into a deterministic meta-model input."""
    probabilities = np.moveaxis(np.asarray(scores, dtype=np.float64), 0, 1)
    raw = probabilities.reshape(probabilities.shape[0], -1)
    logged = np.log(np.clip(probabilities, 1e-7, 1.0))
    logged = logged.reshape(logged.shape[0], -1)
    if view == "probabilities":
        return raw
    if view == "log-probabilities":
        return logged
    if view == "probabilities+log":
        return np.concatenate([raw, logged], axis=1)
    raise ValueError(f"unknown feature view: {view}")


def candidate_models():
    for view in ("probabilities", "log-probabilities", "probabilities+log"):
        for balanced in (False, True):
            class_weight = "balanced" if balanced else None
            for c_value in (0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0):
                yield {
                    "family": "logistic-regression", "view": view,
                    "balanced": balanced, "C": c_value,
                }, make_pipeline(
                    StandardScaler(),
                    LogisticRegression(
                        C=c_value, class_weight=class_weight, max_iter=5000,
                        solver="lbfgs", random_state=20261107,
                    ),
                )
        for balanced in (False, True):
            class_weight = "balanced" if balanced else None
            for depth in (None, 6, 12):
                for minimum_leaf in (1, 2, 4):
                    yield {
                        "family": "extra-trees", "view": view,
                        "balanced": balanced, "maxDepth": depth,
                        "minimumLeaf": minimum_leaf,
                    }, ExtraTreesClassifier(
                        n_estimators=400, max_depth=depth,
                        min_samples_leaf=minimum_leaf, class_weight=class_weight,
                        max_features="sqrt", n_jobs=-1, random_state=20261107,
                    )
            for depth in (6, 12, None):
                for minimum_leaf in (1, 3):
                    yield {
                        "family": "random-forest", "view": view,
                        "balanced": balanced, "maxDepth": depth,
                        "minimumLeaf": minimum_leaf,
                    }, RandomForestClassifier(
                        n_estimators=400, max_depth=depth,
                        min_samples_leaf=minimum_leaf, class_weight=class_weight,
                        max_features="sqrt", n_jobs=-1, random_state=20261107,
                    )
            for c_value in (0.1, 0.3, 1.0, 3.0, 10.0):
                for gamma in ("scale", 0.01, 0.03, 0.1):
                    yield {
                        "family": "rbf-svm", "view": view,
                        "balanced": balanced, "C": c_value, "gamma": gamma,
                    }, make_pipeline(
                        StandardScaler(),
                        SVC(
                            C=c_value, gamma=gamma, class_weight=class_weight,
                            kernel="rbf", random_state=20261107,
                        ),
                    )


def cross_validate(scores, expected, selection_metric="macro-f1", folds=5):
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=20261107)
    best = None
    for specification, estimator in candidate_models():
        features = feature_view(scores, specification["view"])
        fold_f1 = []
        fold_accuracy = []
        for train_indices, validation_indices in splitter.split(features, expected):
            estimator.fit(features[train_indices], expected[train_indices])
            predicted = estimator.predict(features[validation_indices])
            fold_f1.append(f1_score(
                expected[validation_indices], predicted, average="macro",
                zero_division=0,
            ))
            fold_accuracy.append(accuracy_score(expected[validation_indices], predicted))
        result = {
            "specification": specification,
            "meanMacroF1": float(np.mean(fold_f1)),
            "macroF1Std": float(np.std(fold_f1)),
            "meanAccuracy": float(np.mean(fold_accuracy)),
            "accuracyStd": float(np.std(fold_accuracy)),
        }
        if selection_metric == "accuracy":
            key = (result["meanAccuracy"], result["meanMacroF1"], -result["accuracyStd"])
        else:
            key = (result["meanMacroF1"], result["meanAccuracy"], -result["macroF1Std"])
        if best is None or key > best[0]:
            best = (key, result, estimator)
    return best[1], best[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--model", required=True, action="append", type=parse_model)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--selection-metric", choices=("macro-f1", "accuracy"), default="macro-f1",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new path")
    if len(args.model) < 2:
        parser.error("at least two models are required")

    rows = read_reviewed_manifest(args.manifest)
    outputs = infer(rows, args.model)
    validation = outputs["val"]
    selection, estimator = cross_validate(
        validation["scores"], validation["expected"], args.selection_metric
    )
    validation_features = feature_view(
        validation["scores"], selection["specification"]["view"]
    )
    estimator.fit(validation_features, validation["expected"])
    validation_predictions = estimator.predict(validation_features)

    test = outputs["test"]
    test_features = feature_view(test["scores"], selection["specification"]["view"])
    test_predictions = estimator.predict(test_features)
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "validation-cross-validated-stacker-development-probe",
        "selectionRule": (
            "maximum mean cross-validated validation accuracy, then macro F1"
            if args.selection_metric == "accuracy"
            else "maximum mean validation macro F1, then accuracy"
        ),
        "manifest": {"path": str(args.manifest), "sha256": sha256(args.manifest)},
        "models": [
            {"modelId": model_id, "path": str(path), "sha256": sha256(path)}
            for model_id, path in args.model
        ],
        "crossValidation": selection,
        "validationRefit": metrics(validation["expected"], validation_predictions),
        "test": metrics(test["expected"], test_predictions),
        "limitations": [
            "The meta-model was selected only through cross-validation inside the validation split.",
            "The frozen test split has been reused by earlier development experiments.",
            "This result is not field accuracy and does not replace external validation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
