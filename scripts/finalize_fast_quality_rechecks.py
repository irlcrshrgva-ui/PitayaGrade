"""Validate and apply the two compact human A/B/C recheck CSV files.

The original ZIPs are treated as immutable assignments. Returned CSVs may edit
only confirmed_label and review_note. Frozen test rows are never accepted.
"""
import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scripts.reviewed_training import ROOT, validation


LABELS = {"Grade A", "Grade B", "Grade C", "Reject"}
EDITABLE_FIELDS = {"confirmed_label", "review_note"}
NUMERIC_PRESENTATION_FIELDS = {"priority", "ensemble_confidence"}


def immutable_values_match(field, returned, original):
    returned = returned or ""
    original = original or ""
    if returned == original:
        return True
    if field in NUMERIC_PRESENTATION_FIELDS:
        try:
            return float(returned) == float(original)
        except ValueError:
            return False
    return False


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_completed(value):
    try:
        reviewer, raw_path = value.split("=", 1)
    except ValueError as error:
        raise argparse.ArgumentTypeError("completed file must be REVIEWER_ID=CSV") from error
    path = Path(raw_path)
    if not reviewer.strip() or not path.is_file():
        raise argparse.ArgumentTypeError(f"completed file is unavailable: {value}")
    return reviewer.strip(), path


def read_csv_bytes(payload):
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))


def read_csv_file(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_assignment(path):
    with zipfile.ZipFile(path) as bundle:
        audit = json.loads(bundle.read("audit.json"))
        rows = read_csv_bytes(bundle.read("review.csv"))
    reviewer = str(audit.get("reviewerId") or "").strip()
    if not reviewer or audit.get("testRecordsIncluded") != 0:
        raise ValueError(f"{path}: invalid assignment audit")
    if audit.get("recordCount") != len(rows):
        raise ValueError(f"{path}: assignment count does not match audit")
    return reviewer, audit, rows


def row_map(rows, context):
    mapped = {}
    for row in rows:
        identifier = (row.get("id") or "").strip()
        if not identifier or identifier in mapped:
            raise ValueError(f"{context}: missing or duplicate id {identifier!r}")
        mapped[identifier] = row
    return mapped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-manifest", required=True, type=Path)
    parser.add_argument("--package", required=True, action="append", type=Path)
    parser.add_argument("--completed", required=True, action="append", type=parse_completed)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--allow-missing-change-notes", action="store_true",
        help="Accept changed labels with blank notes while recording the waiver in the audit",
    )
    parser.add_argument(
        "--normalize-known-label-typos", action="store_true",
        help="Normalize the known typo 'Grabe B' to 'Grade B' and record every change",
    )
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("output directory already exists; evidence is never overwritten")

    base_hash = sha256(args.base_manifest)
    base_rows = json.loads(args.base_manifest.read_text(encoding="utf-8"))
    if not isinstance(base_rows, list):
        parser.error("base manifest must be a JSON array")
    base_by_id = {row.get("id"): row for row in base_rows}

    assignments = {}
    for package in args.package:
        reviewer, audit, rows = load_assignment(package)
        if reviewer in assignments:
            parser.error(f"duplicate assignment reviewer: {reviewer}")
        if audit.get("manifest", {}).get("sha256") != base_hash:
            parser.error(f"{package}: base manifest checksum mismatch")
        assignments[reviewer] = {"package": package, "audit": audit, "rows": rows}

    completed = dict(args.completed)
    if set(completed) != set(assignments):
        parser.error(
            "completed reviewer IDs must exactly match assignments; "
            f"expected {sorted(assignments)}, received {sorted(completed)}")

    patches = []
    normalized_labels = []
    missing_change_notes = []
    groups = defaultdict(list)
    for reviewer in sorted(assignments):
        assignment = assignments[reviewer]
        original = row_map(assignment["rows"], f"{reviewer} assignment")
        returned_rows = read_csv_file(completed[reviewer])
        returned = row_map(returned_rows, f"{reviewer} completed CSV")
        if set(returned) != set(original):
            missing = sorted(set(original) - set(returned))
            extra = sorted(set(returned) - set(original))
            parser.error(f"{reviewer}: row identities changed; missing={missing[:5]} extra={extra[:5]}")
        for identifier in sorted(original):
            source = original[identifier]
            result = returned[identifier]
            if set(result) != set(source):
                parser.error(f"{reviewer}/{identifier}: CSV columns changed")
            for field in source:
                if field not in EDITABLE_FIELDS and not immutable_values_match(
                        field, result.get(field), source.get(field)):
                    parser.error(f"{reviewer}/{identifier}: immutable field changed: {field}")
            raw_confirmed = result.get("confirmed_label") or ""
            confirmed = raw_confirmed.strip()
            if args.normalize_known_label_typos:
                confirmed = {
                    "grade a": "Grade A", "grade b": "Grade B",
                    "grade c": "Grade C", "reject": "Reject",
                    "grabe b": "Grade B",
                }.get(confirmed.lower(), confirmed)
            if confirmed != raw_confirmed:
                normalized_labels.append({
                    "id": identifier, "reviewerId": reviewer,
                    "originalValue": raw_confirmed, "normalizedValue": confirmed,
                })
            note = (result.get("review_note") or "").strip()
            if confirmed not in LABELS:
                parser.error(
                    f"{reviewer}/{identifier}: confirmed_label must be Grade A, Grade B, "
                    "Grade C, or Reject"
                )
            if confirmed != source["current_label"] and not note:
                if not args.allow_missing_change_notes:
                    parser.error(f"{reviewer}/{identifier}: changed labels require review_note")
                missing_change_notes.append({
                    "id": identifier, "reviewerId": reviewer,
                    "priorLabel": source["current_label"], "confirmedLabel": confirmed,
                })
            if source.get("split") not in {"train", "val"}:
                parser.error(f"{reviewer}/{identifier}: frozen test rows are forbidden")
            base = base_by_id.get(identifier)
            if not base or base.get("task") != "quality":
                parser.error(f"{reviewer}/{identifier}: unknown quality record")
            if base.get("candidateSplit") != source.get("split") or \
                    base.get("reviewedSourceGroup") != source.get("source_group") or \
                    base.get("reviewedLabel") != source.get("current_label"):
                parser.error(f"{reviewer}/{identifier}: assignment no longer matches base manifest")
            patch = {
                "id": identifier, "reviewerId": reviewer,
                "sourceGroup": source["source_group"], "split": source["split"],
                "priorLabel": source["current_label"], "confirmedLabel": confirmed,
                "reviewNote": note,
            }
            patches.append(patch)
            groups[(base.get("task"), source["source_group"])].append(patch)

    for (_, source_group), items in groups.items():
        labels = {item["confirmedLabel"] for item in items}
        if len(labels) != 1:
            parser.error(f"source group {source_group}: conflicting confirmed labels {sorted(labels)}")
        assigned_ids = {item["id"] for item in items}
        unassigned = [row for row in base_rows if row.get("task") == "quality" and
                      row.get("reviewedSourceGroup") == source_group and row.get("id") not in assigned_ids]
        if unassigned and any(row.get("reviewedLabel") not in labels for row in unassigned):
            parser.error(f"source group {source_group}: unassigned rows conflict with the confirmed label")

    merge_recorded_at = datetime.now(timezone.utc).isoformat()
    patch_by_id = {row["id"]: row for row in patches}
    candidate = []
    for row in base_rows:
        updated = dict(row)
        patch = patch_by_id.get(row.get("id"))
        if patch:
            updated["reviewedLabel"] = patch["confirmedLabel"]
            updated["fastRecheck"] = {
                "reviewerId": patch["reviewerId"],
                "priorLabel": patch["priorLabel"],
                "confirmedLabel": patch["confirmedLabel"],
                "reviewNote": patch["reviewNote"],
                "mergeRecordedAt": merge_recorded_at,
            }
        candidate.append(updated)

    errors = validation.validate(candidate, "manuscript-quality", root=ROOT)
    if errors:
        parser.error("candidate manifest failed validation:\n" + "\n".join(errors[:20]))

    args.output_dir.mkdir(parents=True)
    patch_path = args.output_dir / "validated-recheck-patch.json"
    candidate_path = args.output_dir / "candidate-manifest.json"
    patch_path.write_text(json.dumps(patches, indent=2) + "\n", encoding="utf-8")
    candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    audit = {
        "schemaVersion": 1,
        "status": (
            "human-fast-rechecks-validated-with-explicit-waivers-and-applied-to-candidate"
            if missing_change_notes or normalized_labels
            else "human-fast-rechecks-validated-and-applied-to-candidate"
        ),
        "mergeRecordedAt": merge_recorded_at,
        "baseManifest": {"path": str(args.base_manifest), "sha256": base_hash},
        "assignments": [{
            "reviewerId": reviewer,
            "package": str(assignments[reviewer]["package"]),
            "packageSha256": sha256(assignments[reviewer]["package"]),
            "completedCsv": str(completed[reviewer]),
            "completedCsvSha256": sha256(completed[reviewer]),
        } for reviewer in sorted(assignments)],
        "recordsValidated": len(patches),
        "labelsChanged": sum(row["priorLabel"] != row["confirmedLabel"] for row in patches),
        "missingChangeNoteCount": len(missing_change_notes),
        "missingChangeNotes": missing_change_notes,
        "normalizedLabelCount": len(normalized_labels),
        "normalizedLabels": normalized_labels,
        "operatorPolicy": {
            "allowedMissingChangeNotes": args.allow_missing_change_notes,
            "normalizedKnownLabelTypos": args.normalize_known_label_typos,
        },
        "frozenTestRecordsIncluded": 0,
        "patchSha256": sha256(patch_path),
        "candidateManifestSha256": sha256(candidate_path),
        "validationErrors": 0,
    }
    (args.output_dir / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
