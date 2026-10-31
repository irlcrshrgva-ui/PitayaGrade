"""Stage the verified quality-model evidence as a portable Week 4 package.

This deliberately creates a quality-only package. It never creates device, UAT,
or disease evidence and therefore cannot make the final release gate pass.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


MODEL_SOURCES = (
    {
        "id": "mobilenetv2-quality",
        "name": "MobileNetV2",
        "version": "final-quality-2026-10-27",
        "evaluation": "training_results/final-quality-2026-10-27/held-out-summary/evaluation.json",
        "predictions": "training_results/final-quality-2026-10-27/MobileNetV2_onnx_predictions.csv",
        "confusion": "training_results/final-quality-2026-10-27/held-out-summary/confusion-mobilenetv2-quality.csv",
        "runtime": "training_results/final-quality-2026-10-27/runtime-verification/mobilenetv2-quality.json",
        "model": "www/model/quality/mobilenetv2.onnx",
    },
    {
        "id": "resnet50-quality",
        "name": "ResNet50",
        "version": "final-quality-2026-10-27",
        "evaluation": "training_results/final-quality-2026-10-27/held-out-summary/evaluation.json",
        "predictions": "training_results/final-quality-2026-10-27/ResNet50_onnx_predictions.csv",
        "confusion": "training_results/final-quality-2026-10-27/held-out-summary/confusion-resnet50-quality.csv",
        "runtime": "training_results/final-quality-2026-10-27/runtime-verification/resnet50-quality.json",
        "model": "www/model/quality/resnet50.onnx",
    },
    {
        "id": "efficientnet-b3-quality",
        "name": "EfficientNet-B3",
        "version": "external-pretrained-quality-2026-10-30-efficientnetb3",
        "evaluation": "training_results/external-pretrained-quality-2026-10-30-efficientnetb3/held-out-summary/evaluation.json",
        "predictions": "training_results/external-pretrained-quality-2026-10-30-efficientnetb3/EfficientNetB3_onnx_predictions.csv",
        "confusion": "training_results/external-pretrained-quality-2026-10-30-efficientnetb3/held-out-summary/confusion-efficientnet-b3-quality.csv",
        "runtime": "training_results/external-pretrained-quality-2026-10-30-efficientnetb3/runtime-verification/efficientnet-b3-quality.json",
        "model": "www/model/quality/efficientnet-b3.onnx",
    },
)

EVALUATION_FIELDS = (
    "evaluation_id", "evaluated_at", "task", "model_id", "model_name", "model_version",
    "model_path", "model_sha256", "runtime_verification_path", "test_manifest",
    "test_manifest_sha256", "test_sample_count", "classes", "input_size",
    "confidence_threshold", "device", "runtime", "accuracy", "macro_precision",
    "macro_recall", "macro_f1", "map50", "map50_95", "mask_map50",
    "mean_latency_ms", "p95_latency_ms", "failed_samples", "confusion_matrix_path",
    "predictions_path", "notes", "reviewer",
)
PREDICTION_FIELDS = ("model_id", "sample_id", "predicted_label", "confidence", "inference_ms")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(target: Path, base: Path) -> str:
    return Path(__import__("os").path.relpath(target.resolve(), base.resolve())).as_posix()


def read_predictions(path: Path, model_id: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or set(PREDICTION_FIELDS) - set(rows[0]):
        raise ValueError(f"Invalid prediction export: {path}")
    if any(row["model_id"] != model_id for row in rows):
        raise ValueError(f"Prediction export contains a different model ID: {path}")
    sample_ids = [row["sample_id"] for row in rows]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError(f"Prediction export contains duplicate samples: {path}")
    return rows


def stage_quality_evidence(root: Path, output: Path) -> dict:
    root = root.resolve()
    output = output.resolve()
    if not output.is_relative_to(root):
        raise ValueError("Output must be inside the PitayaGrade project so evidence paths stay portable")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    manifest_source = root / "local-review/finalized-human-review-2026-10-27/frozen-quality-manifest.json"
    audit_source = root / "local-review/finalized-human-review-2026-10-27/finalization-audit.json"
    manifest_hash = file_hash(manifest_source)
    finalization = json.loads(audit_source.read_text(encoding="utf-8"))
    if finalization.get("status") != "human-reviewed-and-validated" or finalization.get("validationErrors") != 0:
        raise ValueError("Quality finalization audit is not valid")
    if finalization.get("frozenQualityManifestSha256") != manifest_hash:
        raise ValueError("Frozen quality manifest does not match its finalization audit")

    manifest_target = output / "frozen-quality-manifest.json"
    audit_target = output / "quality-finalization-audit.json"
    shutil.copy2(manifest_source, manifest_target)
    shutil.copy2(audit_source, audit_target)

    evaluation_rows: list[dict[str, object]] = []
    combined_predictions: list[dict[str, str]] = []
    model_records = []
    for source in MODEL_SOURCES:
        evaluation_source = root / source["evaluation"]
        evaluation = json.loads(evaluation_source.read_text(encoding="utf-8"))
        if evaluation.get("manifest", {}).get("sha256") != manifest_hash:
            raise ValueError(f"{source['id']} was not evaluated on the frozen quality manifest")
        metrics = next((item for item in evaluation.get("models", []) if item.get("modelId") == source["id"]), None)
        if metrics is None:
            raise ValueError(f"Missing held-out metrics for {source['id']}")

        model_source = root / source["model"]
        runtime_source = root / source["runtime"]
        predictions_source = root / source["predictions"]
        confusion_source = root / source["confusion"]
        model_hash = file_hash(model_source)
        runtime = json.loads(runtime_source.read_text(encoding="utf-8"))
        if runtime.get("modelId") != source["id"] or runtime.get("sha256") != model_hash or runtime.get("runtimeCompatible") is not True:
            raise ValueError(f"Runtime verification does not match {source['id']}")

        predictions = read_predictions(predictions_source, source["id"])
        if len(predictions) != metrics["sampleCount"]:
            raise ValueError(f"Prediction count does not match held-out metrics for {source['id']}")
        combined_predictions.extend({field: row[field] for field in PREDICTION_FIELDS} for row in predictions)

        prediction_target = output / f"predictions-{source['id']}.csv"
        confusion_target = output / f"confusion-{source['id']}.csv"
        runtime_target = output / f"runtime-{source['id']}.json"
        shutil.copy2(predictions_source, prediction_target)
        shutil.copy2(confusion_source, confusion_target)
        shutil.copy2(runtime_source, runtime_target)

        evaluation_rows.append({
            "evaluation_id": f"quality-{source['id']}-held-out-2026-10",
            "evaluated_at": evaluation["generatedAt"],
            "task": "quality",
            "model_id": source["id"],
            "model_name": source["name"],
            "model_version": source["version"],
            "model_path": relative_path(model_source, output),
            "model_sha256": model_hash,
            "runtime_verification_path": runtime_target.name,
            "test_manifest": manifest_target.name,
            "test_manifest_sha256": manifest_hash,
            "test_sample_count": metrics["sampleCount"],
            "classes": "Grade A|Grade B|Grade C|Reject",
            "input_size": 224,
            "confidence_threshold": "",
            "device": "Windows CPU",
            "runtime": "ONNX Runtime",
            "accuracy": metrics["accuracy"],
            "macro_precision": metrics["macroPrecision"],
            "macro_recall": metrics["macroRecall"],
            "macro_f1": metrics["macroF1"],
            "map50": "",
            "map50_95": "",
            "mask_map50": "",
            "mean_latency_ms": metrics["meanLatencyMs"],
            "p95_latency_ms": metrics["p95LatencyMs"],
            "failed_samples": 0,
            "confusion_matrix_path": confusion_target.name,
            "predictions_path": prediction_target.name,
            "notes": "Exact frozen held-out ONNX evaluation; field performance remains untested.",
            "reviewer": "automated-evaluation-pipeline",
        })
        model_records.append({
            "modelId": source["id"],
            "modelSha256": model_hash,
            "evaluationSource": source["evaluation"],
            "evaluationSourceSha256": file_hash(evaluation_source),
            "predictionsSha256": file_hash(prediction_target),
            "confusionMatrixSha256": file_hash(confusion_target),
            "runtimeVerificationSha256": file_hash(runtime_target),
        })

    evaluation_target = output / "model-evaluation.csv"
    with evaluation_target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVALUATION_FIELDS)
        writer.writeheader()
        writer.writerows(evaluation_rows)

    combined_target = output / "predictions.csv"
    with combined_target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREDICTION_FIELDS)
        writer.writeheader()
        writer.writerows(combined_predictions)

    package_files = sorted(path for path in output.iterdir() if path.is_file())
    audit = {
        "status": "quality-only-verified-release-incomplete",
        "purpose": "Portable Week 4 evidence for the three selectable quality classifiers.",
        "releaseReady": False,
        "testManifestSha256": manifest_hash,
        "testSampleCountPerModel": 226,
        "models": model_records,
        "files": {path.name: {"sha256": file_hash(path), "bytes": path.stat().st_size} for path in package_files},
        "missingReleaseEvidence": [
            "evaluated YOLOv8-Nano detector row",
            "human-reviewed disease annotations and evaluated disease-segmentation row",
            "physical Android device-test.csv",
            "human UAT uat.csv",
            "signed release audit",
        ],
    }
    audit_target = output / "quality-evidence-audit.json"
    audit_target.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = stage_quality_evidence(args.root, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
