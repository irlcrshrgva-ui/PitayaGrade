"""Probe an ordinal A/B/C classifier with a separate Reject gate.

All fitting uses train rows. Model settings and decision thresholds are selected
only on validation macro F1/accuracy. The reused test split is evaluated once
after selection and is not a fresh field-accuracy estimate.
"""
import argparse
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


CLASS_NAMES = ["Grade A", "Grade B", "Grade C", "Reject"]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metrics(expected, predicted):
    expected = np.asarray(expected, dtype=np.int64)
    predicted = np.asarray(predicted, dtype=np.int64)
    return {
        "correct": int((expected == predicted).sum()),
        "count": int(expected.size),
        "accuracy": float((expected == predicted).mean()),
        "macroF1": float(f1_score(expected, predicted, labels=range(4), average="macro", zero_division=0)),
        "confusionMatrix": confusion_matrix(expected, predicted, labels=range(4)).tolist(),
    }


def feature_views(cnn, dino, split):
    values = cnn[split]
    return {
        "cnn-mean": values.mean(axis=1),
        "cnn-flat": values.reshape(values.shape[0], -1),
        "cnn-mean+dino": np.concatenate([values.mean(axis=1), dino[split]], axis=1),
    }


def fit_binary(x, target, c_value, balanced):
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=c_value, class_weight="balanced" if balanced else None,
            max_iter=4000, solver="lbfgs", random_state=42),
    ).fit(x, target)


def probabilities(models, x):
    reject, above_a, above_b = models
    return (
        reject.predict_proba(x)[:, 1],
        above_a.predict_proba(x)[:, 1],
        above_b.predict_proba(x)[:, 1],
    )


def decide(values, thresholds):
    reject_probability, above_a_probability, above_b_probability = values
    reject_threshold, a_threshold, b_threshold = thresholds
    predicted = np.zeros(len(reject_probability), dtype=np.int64)
    predicted[above_a_probability >= a_threshold] = 1
    predicted[above_b_probability >= b_threshold] = 2
    predicted[reject_probability >= reject_threshold] = 3
    return predicted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnn-features", required=True, type=Path)
    parser.add_argument("--dino-features", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new path")

    cnn = np.load(args.cnn_features)
    dino = np.load(args.dino_features)
    for key in ("trainLabels", "validationLabels", "testLabels"):
        if not np.array_equal(cnn[key], dino[key]):
            raise ValueError(f"feature caches disagree on {key}")

    views = {split: feature_views(cnn, dino, split) for split in ("train", "validation", "test")}
    train_labels = cnn["trainLabels"]
    validation_labels = cnn["validationLabels"]
    threshold_values = np.arange(0.30, 0.701, 0.05)
    best = None
    leaderboard = []
    for view_name in views["train"]:
        train_x = views["train"][view_name]
        grade_mask = train_labels < 3
        for c_value in (0.01, 0.03, 0.1, 0.3, 1.0, 3.0):
            for balanced in (False, True):
                models = (
                    fit_binary(train_x, train_labels == 3, c_value, balanced),
                    fit_binary(train_x[grade_mask], train_labels[grade_mask] > 0, c_value, balanced),
                    fit_binary(train_x[grade_mask], train_labels[grade_mask] > 1, c_value, balanced),
                )
                validation_probabilities = probabilities(models, views["validation"][view_name])
                local_best = None
                for thresholds in itertools.product(threshold_values, repeat=3):
                    result = metrics(validation_labels, decide(validation_probabilities, thresholds))
                    key = (result["macroF1"], result["accuracy"])
                    if local_best is None or key > local_best[0]:
                        local_best = (key, tuple(float(value) for value in thresholds), result)
                row = {
                    "view": view_name, "C": c_value, "balanced": balanced,
                    "thresholds": local_best[1], "validation": local_best[2],
                }
                leaderboard.append(row)
                key = (*local_best[0], -c_value)
                if best is None or key > best[0]:
                    best = (key, row, models)
                print(
                    f"{view_name} C={c_value:g} balanced={balanced}: "
                    f"val accuracy={local_best[2]['accuracy']:.4f} "
                    f"macroF1={local_best[2]['macroF1']:.4f}", flush=True)

    selected = best[1]
    test_predictions = decide(
        probabilities(best[2], views["test"][selected["view"]]),
        selected["thresholds"],
    )
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "validation-selected-development-probe-not-field-accuracy",
        "selectionRule": "maximum validation macro F1, then validation accuracy",
        "classOrder": CLASS_NAMES,
        "inputs": {
            "cnnFeatures": {"path": str(args.cnn_features), "sha256": sha256(args.cnn_features)},
            "dinoFeatures": {"path": str(args.dino_features), "sha256": sha256(args.dino_features)},
        },
        "selected": {key: value for key, value in selected.items() if key != "validation"},
        "validation": selected["validation"],
        "test": metrics(cnn["testLabels"], test_predictions),
        "leaderboard": sorted(
            leaderboard,
            key=lambda row: (row["validation"]["macroF1"], row["validation"]["accuracy"]),
            reverse=True,
        )[:20],
        "limitations": [
            "The frozen test split has been used by earlier development experiments.",
            "This result is not field accuracy and does not replace external validation.",
            "No labels or production model assets were changed.",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selected": report["selected"], "validation": report["validation"], "test": report["test"]}, indent=2))


if __name__ == "__main__":
    main()
