"""Create two compact, human-only A/B/C recheck ZIP packages.

Models rank uncertain records but never replace the reviewed label. Test records
are excluded so this workflow cannot tune against the frozen evaluation answers.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np

from scripts.ensemble_quality_probe import parse_model, sha256
from scripts.evaluate_quality_onnx import CLASS_NAMES, preprocess, probabilities
from scripts.reviewed_training import ROOT, read_reviewed_manifest


def priority_score(label_index, model_probabilities):
    averaged = np.mean(model_probabilities, axis=0)
    predictions = np.argmax(model_probabilities, axis=1)
    disagreement = len(set(int(value) for value in predictions)) / len(predictions)
    mismatch = float(int(np.argmax(averaged)) != label_index)
    confidence = float(np.max(averaged))
    entropy = float(-np.sum(averaged * np.log(np.maximum(averaged, 1e-12))) / math.log(len(CLASS_NAMES)))
    priority = min(1.0, 0.35 * disagreement + 0.30 * mismatch + 0.20 * (1 - confidence) + 0.15 * entropy)
    return priority, averaged, predictions


def rank_rows(rows, models):
    import onnxruntime as ort

    sessions = []
    for model_id, path in models:
        session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        sessions.append((model_id, path, session, session.get_inputs()[0].name))
    label_index = {label: index for index, label in enumerate(CLASS_NAMES)}
    candidates = []
    selected = [row for row in rows if row.get("candidateSplit") in {"train", "val"}
                and row.get("reviewedLabel") in CLASS_NAMES[:3]]
    for position, row in enumerate(selected, 1):
        tensor = preprocess(ROOT / row["image"])
        scores = []
        for _, _, session, input_name in sessions:
            scores.append(probabilities(session.run(None, {input_name: tensor})[0]))
        scores = np.asarray(scores)
        priority, averaged, predictions = priority_score(label_index[row["reviewedLabel"]], scores)
        candidates.append({
            "row": row,
            "priority": priority,
            "ensembleLabel": CLASS_NAMES[int(np.argmax(averaged))],
            "ensembleConfidence": float(np.max(averaged)),
            "modelLabels": [CLASS_NAMES[int(value)] for value in predictions],
        })
        if position % 100 == 0:
            print(f"Ranked {position}/{len(selected)} A/B/C records", flush=True)
    return candidates


def select_groups(candidates, limit):
    grouped = defaultdict(list)
    for candidate in candidates:
        row = candidate["row"]
        key = (row.get("task"), str(row.get("reviewedSourceGroup") or row["id"]))
        grouped[key].append(candidate)
    ordered = sorted(grouped.values(), key=lambda group: (-max(item["priority"] for item in group), group[0]["row"]["id"]))
    chosen = []
    count = 0
    for group in ordered:
        if count >= limit:
            break
        chosen.append(group)
        count += len(group)
    return chosen


def assign_groups(groups, reviewer_count):
    assignments = [[] for _ in range(reviewer_count)]
    counts = [0] * reviewer_count
    for group in sorted(groups, key=lambda value: (-len(value), -max(item["priority"] for item in value))):
        index = min(range(reviewer_count), key=lambda value: (counts[value], value))
        assignments[index].extend(group)
        counts[index] += len(group)
    return assignments


def csv_bytes(items):
    stream = io.StringIO(newline="")
    fields = ["id", "split", "source_group", "current_label", "confirmed_label",
              "review_note", "priority", "ensemble_suggestion", "ensemble_confidence",
              "individual_model_suggestions", "image_file"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for item in sorted(items, key=lambda value: (-value["priority"], value["row"]["id"])):
        row = item["row"]
        suffix = Path(row["image"]).suffix.lower()
        image_file = f"images/{row['id'].replace(':', '-')}{suffix}"
        writer.writerow({
            "id": row["id"], "split": row["candidateSplit"],
            "source_group": row["reviewedSourceGroup"], "current_label": row["reviewedLabel"],
            "confirmed_label": "", "review_note": "", "priority": f"{item['priority']:.6f}",
            "ensemble_suggestion": item["ensembleLabel"],
            "ensemble_confidence": f"{item['ensembleConfidence']:.6f}",
            "individual_model_suggestions": " | ".join(item["modelLabels"]),
            "image_file": image_file,
        })
    return stream.getvalue().encode("utf-8-sig")


def write_package(output, reviewer_id, items, models, manifest):
    archive = output / f"{reviewer_id}-fast-quality-recheck.zip"
    instructions = f"""PitayaGrade fast A/B/C recheck — {reviewer_id}

1. Extract this ZIP permanently.
2. Open review.csv in Excel or Google Sheets.
3. Open each image listed in image_file.
4. Ignore the model suggestions until after making your own visual decision.
5. Enter only Grade A, Grade B, or Grade C in confirmed_label.
6. Add a short review_note whenever you change the current label.
7. Do not edit id, split, source_group, current_label or image_file.
8. Return the completed review.csv to the coordinator.

The model columns only prioritize difficult records. They are not ground truth.
This package excludes every frozen test record.
"""
    audit = {
        "schemaVersion": 1,
        "purpose": "human A/B/C adjudication; model ranking is not ground truth",
        "reviewerId": reviewer_id,
        "recordCount": len(items),
        "manifest": {"path": str(manifest), "sha256": sha256(manifest)},
        "models": [{"modelId": model_id, "path": str(path), "sha256": sha256(path)}
                   for model_id, path in models],
        "testRecordsIncluded": 0,
    }
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        bundle.writestr("INSTRUCTIONS.txt", instructions)
        bundle.writestr("review.csv", csv_bytes(items))
        bundle.writestr("audit.json", json.dumps(audit, indent=2) + "\n")
        for item in items:
            row = item["row"]
            source = ROOT / row["image"]
            if hashlib.sha256(source.read_bytes()).hexdigest() != row["fileSha256"]:
                raise ValueError(f"image checksum mismatch: {row['id']}")
            suffix = source.suffix.lower()
            bundle.write(source, f"images/{row['id'].replace(':', '-')}{suffix}")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--model", required=True, action="append", type=parse_model)
    parser.add_argument("--limit", type=int, default=180)
    parser.add_argument("--reviewers", type=int, default=2)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.limit < 1 or args.reviewers < 1:
        parser.error("limit and reviewers must be positive")
    if args.output.exists():
        parser.error("output already exists; choose a new path")
    rows = read_reviewed_manifest(args.manifest)
    ranked = rank_rows(rows, args.model)
    groups = select_groups(ranked, args.limit)
    assignments = assign_groups(groups, args.reviewers)
    args.output.mkdir(parents=True)
    archives = []
    for index, assignment in enumerate(assignments, 1):
        archives.append(write_package(args.output, f"fast-recheck-{index:02d}", assignment,
                                      args.model, args.manifest))
    summary = {
        "selectedRecords": sum(len(value) for value in assignments),
        "selectedGroups": len(groups),
        "frozenTestRecordsIncluded": 0,
        "assignments": [{"reviewerId": f"fast-recheck-{index:02d}", "records": len(value),
                         "archive": str(archives[index - 1])}
                        for index, value in enumerate(assignments, 1)],
    }
    (args.output / "assignment-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
