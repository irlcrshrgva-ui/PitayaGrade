"""Select horizontal-flip test-time augmentation on validation evidence.

The shared original/flip blend and model weights are selected only on the
validation split. The reused test split is evaluated once after selection.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.ensemble_quality_probe import metrics, parse_model, sha256, weight_grid
from scripts.evaluate_quality_onnx import CLASS_NAMES, preprocess, probabilities
from scripts.reviewed_training import ROOT, read_reviewed_manifest


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

    class_to_index = {label: index for index, label in enumerate(CLASS_NAMES)}
    outputs = {}
    for split in ("val", "test"):
        selected = sorted(
            (row for row in rows if row.get("candidateSplit") == split),
            key=lambda row: row["id"],
        )
        expected = np.asarray(
            [class_to_index[row["reviewedLabel"]] for row in selected], dtype=np.int64
        )
        original = np.zeros((len(models), len(selected), len(CLASS_NAMES)), dtype=np.float64)
        flipped = np.zeros_like(original)
        for row_index, row in enumerate(selected):
            tensor = preprocess(ROOT / row["image"])
            flipped_tensor = np.ascontiguousarray(tensor[:, :, :, ::-1])
            for model_index, session in enumerate(sessions):
                input_name = session.get_inputs()[0].name
                original[model_index, row_index] = probabilities(
                    session.run(None, {input_name: tensor})[0]
                )
                flipped[model_index, row_index] = probabilities(
                    session.run(None, {input_name: flipped_tensor})[0]
                )
        outputs[split] = {"expected": expected, "original": original, "flipped": flipped}
    return outputs


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

    rows = read_reviewed_manifest(args.manifest)
    outputs = infer(rows, args.model)
    validation = outputs["val"]
    best = None
    for flip_weight in (0.0, 0.25, 0.5, 0.75, 1.0):
        augmented = (
            (1.0 - flip_weight) * validation["original"]
            + flip_weight * validation["flipped"]
        )
        for weights in weight_grid(len(args.model), args.grid_denominator):
            combined = np.tensordot(weights, augmented, axes=(0, 0))
            result = metrics(validation["expected"], combined.argmax(axis=1))
            key = (result["macroF1"], result["accuracy"], -int((weights == 0).sum()))
            if best is None or key > best[0]:
                best = (key, flip_weight, weights, result)

    _, flip_weight, weights, validation_result = best
    test = outputs["test"]
    test_augmented = (
        (1.0 - flip_weight) * test["original"] + flip_weight * test["flipped"]
    )
    test_scores = np.tensordot(weights, test_augmented, axes=(0, 0))
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "validation-selected-tta-development-probe",
        "selectionRule": "maximum validation macro F1, then accuracy",
        "flipWeight": flip_weight,
        "gridDenominator": args.grid_denominator,
        "manifest": {"path": str(args.manifest), "sha256": sha256(args.manifest)},
        "models": [
            {"modelId": model_id, "path": str(path), "sha256": sha256(path),
             "weight": float(weight)}
            for (model_id, path), weight in zip(args.model, weights)
        ],
        "validation": validation_result,
        "test": metrics(test["expected"], test_scores.argmax(axis=1)),
        "limitations": [
            "The TTA blend and model weights were selected only from validation data.",
            "The frozen test split has been reused by earlier development experiments.",
            "This result is not field accuracy and does not replace external validation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
