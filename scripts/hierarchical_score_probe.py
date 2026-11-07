"""Validation-select a Reject gate and A/B/C grader from aligned model scores."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score

from scripts.ensemble_quality_probe import infer, metrics, parse_model, sha256
from scripts.reviewed_training import read_reviewed_manifest
from scripts.stacked_quality_probe import candidate_models, feature_view


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--model", required=True, action="append", type=parse_model)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new path")

    rows = read_reviewed_manifest(args.manifest)
    outputs = infer(rows, args.model, splits=("train", "val", "test"))
    features = {
        split: feature_view(outputs[split]["scores"], "probabilities+log")
        for split in outputs
    }
    labels = {split: outputs[split]["expected"] for split in outputs}

    gate_candidates = []
    grade_candidates = []
    for specification, model in candidate_models():
        gate = model
        gate.fit(features["train"], (labels["train"] == 3).astype(np.int64))
        predicted = gate.predict(features["val"])
        accuracy = float((predicted == (labels["val"] == 3)).mean())
        score = float(f1_score(labels["val"] == 3, predicted, average="binary", zero_division=0))
        gate_candidates.append((accuracy, score, specification, gate, predicted))

    grade_train = labels["train"] != 3
    grade_val = labels["val"] != 3
    for specification, model in candidate_models():
        grader = model
        grader.fit(features["train"][grade_train], labels["train"][grade_train])
        predicted = grader.predict(features["val"])
        accuracy = float((predicted[grade_val] == labels["val"][grade_val]).mean())
        score = float(f1_score(
            labels["val"][grade_val], predicted[grade_val], labels=range(3),
            average="macro", zero_division=0))
        grade_candidates.append((accuracy, score, specification, grader, predicted))

    gate_candidates.sort(key=lambda row: (row[0], row[1]), reverse=True)
    grade_candidates.sort(key=lambda row: (row[0], row[1]), reverse=True)
    best = None
    for gate in gate_candidates[:25]:
        for grader in grade_candidates[:25]:
            combined = np.asarray(grader[4], dtype=np.int64).copy()
            combined[np.asarray(gate[4]) == 1] = 3
            result = metrics(labels["val"], combined)
            key = (result["accuracy"], result["macroF1"])
            if best is None or key > best[0]:
                best = (key, gate, grader, result)

    _, gate, grader, validation = best
    test_gate = gate[3].predict(features["test"])
    test_combined = np.asarray(grader[3].predict(features["test"]), dtype=np.int64)
    test_combined[np.asarray(test_gate) == 1] = 3
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "validation-selected-hierarchical-score-development-probe",
        "selectionRule": "maximum validation accuracy, then macro F1 among top gate/grader candidates",
        "gate": {"specification": gate[2], "binaryValidationAccuracy": gate[0], "binaryValidationF1": gate[1]},
        "grader": {"specification": grader[2], "gradeOnlyValidationAccuracy": grader[0], "gradeOnlyValidationMacroF1": grader[1]},
        "validation": validation,
        "test": metrics(labels["test"], test_combined),
        "manifest": {"path": str(args.manifest), "sha256": sha256(args.manifest)},
        "models": [
            {"modelId": model_id, "path": str(path), "sha256": sha256(path)}
            for model_id, path in args.model
        ],
        "limitations": [
            "The frozen test split has been reused by earlier development experiments.",
            "This probe is not field accuracy and does not replace external validation.",
            "No production asset is changed by this experiment.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
