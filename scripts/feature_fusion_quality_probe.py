"""Validation-select a stronger quality classifier from retained feature caches.

This development probe fits only on the training split, chooses its feature view
and hyperparameters only on validation macro F1/accuracy, and touches the reused
test split once after selection. It does not alter labels or production assets.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


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


def views(cnn, dino, split):
    cnn_values = cnn[split]
    dino_values = dino[split]
    return {
        "cnn-mean": cnn_values.mean(axis=1),
        "cnn-flat": cnn_values.reshape(cnn_values.shape[0], -1),
        "cnn-mean+dino": np.concatenate([cnn_values.mean(axis=1), dino_values], axis=1),
        "cnn-flat+dino": np.concatenate([cnn_values.reshape(cnn_values.shape[0], -1), dino_values], axis=1),
    }


def candidates():
    for class_weight in (None, "balanced"):
        weight_name = "plain" if class_weight is None else "balanced"
        for c_value in (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0):
            yield (
                f"logistic-{weight_name}-c{c_value:g}",
                make_pipeline(StandardScaler(), LogisticRegression(
                    C=c_value, class_weight=class_weight, max_iter=4000,
                    solver="lbfgs", random_state=42)),
            )
        for c_value in (0.3, 1.0, 3.0, 10.0, 30.0):
            yield (
                f"rbf-svm-{weight_name}-c{c_value:g}",
                make_pipeline(StandardScaler(), SVC(
                    C=c_value, kernel="rbf", gamma="scale",
                    class_weight=class_weight, cache_size=4096, random_state=42)),
            )
    for max_features in ("sqrt", 0.25, 0.5):
        yield (
            f"extra-trees-features-{max_features}",
            ExtraTreesClassifier(
                n_estimators=600, max_features=max_features, min_samples_leaf=2,
                class_weight="balanced", n_jobs=-1, random_state=42),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnn-features", required=True, type=Path)
    parser.add_argument("--dino-features", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--selected-only", action="store_true",
                        help="Reproduce the validation-selected cnn-mean+dino balanced RBF-SVM candidate only.")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new path")

    cnn = np.load(args.cnn_features)
    dino = np.load(args.dino_features)
    for split, label_key in (("train", "trainLabels"), ("validation", "validationLabels"), ("test", "testLabels")):
        if not np.array_equal(cnn[label_key], dino[label_key]):
            raise ValueError(f"feature caches disagree on {split} labels/order")

    split_views = {split: views(cnn, dino, split) for split in ("train", "validation", "test")}
    train_labels = cnn["trainLabels"]
    validation_labels = cnn["validationLabels"]
    leaderboard = []
    best = None
    view_names = ["cnn-mean+dino"] if args.selected_only else list(split_views["train"])
    model_candidates = list(candidates())
    if args.selected_only:
        model_candidates = [item for item in model_candidates if item[0] == "rbf-svm-balanced-c1"]
    for view_name in view_names:
        for model_name, model in model_candidates:
            model.fit(split_views["train"][view_name], train_labels)
            result = metrics(validation_labels, model.predict(split_views["validation"][view_name]))
            row = {"view": view_name, "model": model_name, "validation": result}
            leaderboard.append(row)
            key = (result["macroF1"], result["accuracy"], -len(model_name))
            if best is None or key > best[0]:
                best = (key, view_name, model_name, model, result)
            print(f"{view_name} {model_name}: val accuracy={result['accuracy']:.4f} macroF1={result['macroF1']:.4f}", flush=True)

    _, view_name, model_name, model, validation_result = best
    test_result = metrics(cnn["testLabels"], model.predict(split_views["test"][view_name]))
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "validation-selected-development-probe-not-field-accuracy",
        "selectionRule": "maximum validation macro F1, then validation accuracy",
        "classOrder": CLASS_NAMES,
        "inputs": {
            "cnnFeatures": {"path": str(args.cnn_features), "sha256": sha256(args.cnn_features)},
            "dinoFeatures": {"path": str(args.dino_features), "sha256": sha256(args.dino_features)},
        },
        "selected": {"view": view_name, "model": model_name},
        "validation": validation_result,
        "test": test_result,
        "leaderboard": sorted(
            leaderboard,
            key=lambda row: (row["validation"]["macroF1"], row["validation"]["accuracy"]),
            reverse=True,
        )[:20],
        "limitations": [
            "The frozen test split has been evaluated by earlier development experiments.",
            "This probe is not field accuracy and cannot replace external validation.",
            "No production model is changed by this experiment.",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selected": report["selected"], "validation": validation_result, "test": test_result}, indent=2))


if __name__ == "__main__":
    main()
