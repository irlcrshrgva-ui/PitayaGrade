"""Select a probability ensemble on validation data and evaluate it on test data.

This is a development probe. It never trains on or selects weights from the test
split. Because the repository's test split has been evaluated by earlier model
experiments, its result must not be described as a fresh final field estimate.
"""
import argparse
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.evaluate_quality_onnx import CLASS_NAMES, preprocess, probabilities
from scripts.reviewed_training import ROOT, read_reviewed_manifest


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_model(value):
    try:
        model_id, raw_path = value.split("=", 1)
    except ValueError as error:
        raise argparse.ArgumentTypeError("model must be MODEL_ID=PATH") from error
    path = Path(raw_path)
    if not model_id.strip() or not path.is_file():
        raise argparse.ArgumentTypeError(f"model is unavailable: {value}")
    return model_id.strip(), path


def metrics(expected, predicted):
    expected = np.asarray(expected, dtype=np.int64)
    predicted = np.asarray(predicted, dtype=np.int64)
    confusion = np.zeros((len(CLASS_NAMES), len(CLASS_NAMES)), dtype=np.int64)
    for truth, guess in zip(expected, predicted):
        confusion[truth, guess] += 1
    f1_values = []
    for index in range(len(CLASS_NAMES)):
        true_positive = confusion[index, index]
        false_positive = confusion[:, index].sum() - true_positive
        false_negative = confusion[index, :].sum() - true_positive
        precision = true_positive / max(1, true_positive + false_positive)
        recall = true_positive / max(1, true_positive + false_negative)
        f1_values.append(2 * precision * recall / max(1e-12, precision + recall))
    return {
        "correct": int((expected == predicted).sum()),
        "count": int(expected.size),
        "accuracy": float((expected == predicted).mean()),
        "macroF1": float(np.mean(f1_values)),
        "confusionMatrix": confusion.tolist(),
    }


def weight_grid(model_count, denominator):
    for parts in itertools.product(range(denominator + 1), repeat=model_count):
        if sum(parts) == denominator:
            yield np.asarray(parts, dtype=np.float64) / denominator


def infer(rows, models):
    import onnxruntime as ort

    sessions = []
    for model_id, path in models:
        session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        if list(session.get_inputs()[0].shape) != [1, 3, 224, 224]:
            raise ValueError(f"{model_id}: unexpected input shape")
        if list(session.get_outputs()[0].shape) != [1, len(CLASS_NAMES)]:
            raise ValueError(f"{model_id}: unexpected output shape")
        sessions.append(session)

    split_outputs = {}
    class_to_index = {label: index for index, label in enumerate(CLASS_NAMES)}
    for split in ("val", "test"):
        selected = sorted(
            (row for row in rows if row.get("candidateSplit") == split),
            key=lambda row: row["id"],
        )
        expected = np.asarray(
            [class_to_index[row["reviewedLabel"]] for row in selected], dtype=np.int64
        )
        scores = np.zeros((len(models), len(selected), len(CLASS_NAMES)), dtype=np.float64)
        for row_index, row in enumerate(selected):
            tensor = preprocess(ROOT / row["image"])
            for model_index, session in enumerate(sessions):
                input_name = session.get_inputs()[0].name
                result = session.run(None, {input_name: tensor})[0]
                scores[model_index, row_index] = probabilities(result)
        split_outputs[split] = {"expected": expected, "scores": scores}
    return split_outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--model", required=True, action="append", type=parse_model)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--grid-denominator", type=int, default=20)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new path")
    if len(args.model) < 2:
        parser.error("at least two models are required")
    if not 1 <= args.grid_denominator <= 100:
        parser.error("grid denominator must be between 1 and 100")

    rows = read_reviewed_manifest(args.manifest)
    outputs = infer(rows, args.model)
    validation = outputs["val"]
    best = None
    for weights in weight_grid(len(args.model), args.grid_denominator):
        combined = np.tensordot(weights, validation["scores"], axes=(0, 0))
        result = metrics(validation["expected"], combined.argmax(axis=1))
        key = (result["macroF1"], result["accuracy"], -int((weights == 0).sum()))
        if best is None or key > best[0]:
            best = (key, weights, result)

    weights = best[1]
    test = outputs["test"]
    test_scores = np.tensordot(weights, test["scores"], axes=(0, 0))
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "validation-selected-development-ensemble-not-field-accuracy",
        "selectionRule": "maximum validation macro F1, then validation accuracy",
        "gridDenominator": args.grid_denominator,
        "manifest": {"path": str(args.manifest), "sha256": sha256(args.manifest)},
        "models": [
            {"modelId": model_id, "path": str(path), "sha256": sha256(path),
             "weight": float(weight)}
            for (model_id, path), weight in zip(args.model, weights)
        ],
        "validation": best[2],
        "test": metrics(test["expected"], test_scores.argmax(axis=1)),
        "limitations": [
            "Weights were selected only from the validation split.",
            "The frozen test split has been used by earlier development experiments.",
            "This result is not field accuracy and does not replace external validation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
