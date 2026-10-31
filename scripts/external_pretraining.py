"""Validate external feature-pretraining evidence without changing grade labels."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


ALLOWED_LABELS = {"good", "medium"}
ALLOWED_SPLITS = {"train", "test"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def safe_project_path(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"External pretraining path escapes the project: {value}")
    return path


def read_external_pretraining_audit(
    audit_path: Path,
    frozen_manifest: Path,
    root: Path,
) -> dict[str, object]:
    audit_path = Path(audit_path)
    data = json.loads(audit_path.read_text(encoding="utf-8"))
    if data.get("purpose") != "external feature pretraining only; not official grade ground truth":
        raise ValueError("External audit does not preserve the pretraining-only label contract")

    recorded_frozen = safe_project_path(root, str(data.get("frozenManifest", "")))
    if recorded_frozen != Path(frozen_manifest).resolve():
        raise ValueError("External audit was not checked against this frozen manifest")

    source = data.get("source")
    if not isinstance(source, dict):
        raise ValueError("External audit is missing source provenance")
    archive = safe_project_path(root, str(source.get("archive", "")))
    if not archive.is_file() or file_sha256(archive) != source.get("archiveSha256"):
        raise ValueError("External source archive checksum is missing or changed")

    records = data.get("safeRecords")
    if not isinstance(records, list) or not records:
        raise ValueError("External audit contains no leakage-safe records")
    paths = set()
    file_hashes = set()
    pixel_hashes = set()
    counts = Counter()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid external audit record")
        label = record.get("sourceLabel")
        split = record.get("sourceSplit")
        if label not in ALLOWED_LABELS or split not in ALLOWED_SPLITS:
            raise ValueError("Only audited good/medium train/test records may pretrain")
        relative = str(record.get("path", ""))
        path = safe_project_path(root, relative)
        if relative in paths or not path.is_file():
            raise ValueError(f"Missing or duplicate external image path: {relative}")
        paths.add(relative)
        actual = file_sha256(path)
        if actual != record.get("fileSha256"):
            raise ValueError(f"External image checksum changed: {relative}")
        if actual in file_hashes or record.get("pixelSha256") in pixel_hashes:
            raise ValueError("External safe records still contain an exact duplicate")
        file_hashes.add(actual)
        pixel_hashes.add(record.get("pixelSha256"))
        counts[(split, label)] += 1

    if any(counts[(split, label)] == 0 for split in ALLOWED_SPLITS for label in ALLOWED_LABELS):
        raise ValueError("External pretraining requires both labels in train and validation")
    expected = data.get("counts", {}).get("safeIndependentRecords")
    if expected != len(records):
        raise ValueError("External audit summary does not match its safe records")
    data["validatedCounts"] = {
        f"{split}/{label}": counts[(split, label)]
        for split in sorted(ALLOWED_SPLITS)
        for label in sorted(ALLOWED_LABELS)
    }
    return data
