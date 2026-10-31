"""Audit an external quality-pretraining dataset against frozen PitayaGrade evidence.

The external labels remain pretraining labels. This script never maps them to the
capstone's reviewed Grade A/B/C/Reject targets.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def image_signature(path: Path) -> dict[str, object]:
    file_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with Image.open(path) as image:
        source_pixel_sha = hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()
        rgb = ImageOps.exif_transpose(image).convert("RGB")
        pixel_sha = hashlib.sha256(rgb.tobytes()).hexdigest()
        gray = np.asarray(rgb.convert("L").resize((9, 8), Image.Resampling.LANCZOS))
        dhash_bits = gray[:, 1:] > gray[:, :-1]
        dhash = int.from_bytes(np.packbits(dhash_bits).tobytes(), "big")
        average = np.asarray(rgb.convert("L").resize((8, 8), Image.Resampling.LANCZOS))
        ahash = int.from_bytes(np.packbits(average > average.mean()).tobytes(), "big")
    return {
        "fileSha256": file_sha,
        "sourcePixelSha256": source_pixel_sha,
        "pixelSha256": pixel_sha,
        "dhash": dhash,
        "ahash": ahash,
    }


def inspect_record(record: dict[str, object], root: Path) -> dict[str, object]:
    result = dict(record)
    result.update(image_signature(root / str(record["path"])))
    return result


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def bands(value: int):
    for index in range(8):
        yield index, (value >> (index * 8)) & 255


def external_records(external_root: Path, project_root: Path) -> list[dict[str, object]]:
    records = []
    for path in sorted(external_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        relative = path.relative_to(external_root)
        if len(relative.parts) != 4:
            raise ValueError(f"Unexpected external path structure: {relative}")
        split, fruit, label, _ = relative.parts
        if (
            split not in {"train", "test"}
            or fruit != "dragonfruit"
            or label not in {"good", "medium", "bad"}
        ):
            raise ValueError(f"Unexpected external split/label: {relative}")
        records.append({
            "origin": "external",
            "sourceSplit": split,
            "sourceLabel": label,
            "path": path.relative_to(project_root).as_posix(),
        })
    return records


def frozen_records(manifest: Path) -> list[dict[str, object]]:
    rows = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Frozen quality manifest must be a non-empty JSON array")
    records = []
    for row in rows:
        if row.get("task") != "quality":
            continue
        records.append({
            "origin": "frozen",
            "id": row["id"],
            "candidateSplit": row["candidateSplit"],
            "reviewedLabel": row["reviewedLabel"],
            "path": row["image"],
            "expectedFileSha256": row["fileSha256"],
            "expectedPixelSha256": row["pixelSha256"],
        })
    return records


def inspect_all(records: list[dict[str, object]], root: Path) -> list[dict[str, object]]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        inspected = list(pool.map(lambda row: inspect_record(row, root), records))
    for record in inspected:
        expected_file = record.get("expectedFileSha256")
        expected_pixel = record.get("expectedPixelSha256")
        if expected_file and expected_file != record["fileSha256"]:
            raise ValueError(f"Frozen file checksum changed: {record['path']}")
        if expected_pixel and expected_pixel != record["sourcePixelSha256"]:
            raise ValueError(f"Frozen pixel checksum changed: {record['path']}")
    return inspected


def cross_matches(
    external: list[dict[str, object]], frozen: list[dict[str, object]]
) -> tuple[list[dict[str, object]], set[int]]:
    file_index = defaultdict(list)
    pixel_index = defaultdict(list)
    hash_bands = defaultdict(list)
    for index, row in enumerate(frozen):
        file_index[row["fileSha256"]].append(index)
        pixel_index[row["pixelSha256"]].append(index)
        for band in bands(int(row["dhash"])):
            hash_bands[band].append(index)

    matches = []
    excluded = set()
    for ext_index, row in enumerate(external):
        candidates = set(file_index[row["fileSha256"]])
        candidates.update(pixel_index[row["pixelSha256"]])
        for band in bands(int(row["dhash"])):
            candidates.update(hash_bands[band])
        for frozen_index in sorted(candidates):
            other = frozen[frozen_index]
            file_exact = row["fileSha256"] == other["fileSha256"]
            pixel_exact = row["pixelSha256"] == other["pixelSha256"]
            d_distance = hamming(int(row["dhash"]), int(other["dhash"]))
            a_distance = hamming(int(row["ahash"]), int(other["ahash"]))
            if file_exact or pixel_exact or (d_distance <= 6 and a_distance <= 8):
                excluded.add(ext_index)
                matches.append({
                    "externalPath": row["path"],
                    "externalLabel": row["sourceLabel"],
                    "frozenId": other["id"],
                    "frozenSplit": other["candidateSplit"],
                    "frozenLabel": other["reviewedLabel"],
                    "fileExact": file_exact,
                    "pixelExact": pixel_exact,
                    "dhashDistance": d_distance,
                    "ahashDistance": a_distance,
                })
    return matches, excluded


def deduplicate_external(
    records: list[dict[str, object]], excluded: set[int]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    eligible = [index for index in range(len(records)) if index not in excluded]
    parents = {index: index for index in eligible}

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        parents[find(left)] = find(right)

    file_seen = {}
    pixel_seen = {}
    hash_bands = defaultdict(list)
    for index in eligible:
        row = records[index]
        for key, seen in ((row["fileSha256"], file_seen), (row["pixelSha256"], pixel_seen)):
            if key in seen:
                union(index, seen[key])
            else:
                seen[key] = index
        candidates = set()
        for band in bands(int(row["dhash"])):
            candidates.update(hash_bands[band])
            hash_bands[band].append(index)
        for other_index in candidates:
            other = records[other_index]
            if (
                hamming(int(row["dhash"]), int(other["dhash"])) <= 4
                and hamming(int(row["ahash"]), int(other["ahash"])) <= 6
            ):
                union(index, other_index)

    groups = defaultdict(list)
    for index in eligible:
        groups[find(index)].append(index)
    kept = []
    removed = []
    for indexes in groups.values():
        labels = {records[index]["sourceLabel"] for index in indexes}
        if len(labels) != 1:
            removed.extend(dict(records[index], reason="conflicting external duplicate labels") for index in indexes)
            continue
        ordered = sorted(indexes, key=lambda index: str(records[index]["path"]))
        chosen = dict(records[ordered[0]])
        chosen["duplicateGroupSize"] = len(ordered)
        chosen["fileSha256"] = str(chosen["fileSha256"])
        chosen["pixelSha256"] = str(chosen["pixelSha256"])
        chosen["dhash"] = f"{int(chosen['dhash']):016x}"
        chosen["ahash"] = f"{int(chosen['ahash']):016x}"
        kept.append(chosen)
        removed.extend(dict(records[index], reason="external near-duplicate") for index in ordered[1:])
    return sorted(kept, key=lambda row: str(row["path"])), removed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--frozen-manifest", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    external_root = args.external_root.resolve()
    frozen_manifest = args.frozen_manifest.resolve()
    source_archive = args.source_archive.resolve()
    output = args.output.resolve()
    external = inspect_all(external_records(external_root, project_root), project_root)
    frozen = inspect_all(frozen_records(frozen_manifest), project_root)
    matches, excluded = cross_matches(external, frozen)
    safe, internal_removed = deduplicate_external(external, excluded)
    result = {
        "schemaVersion": 1,
        "purpose": "external feature pretraining only; not official grade ground truth",
        "source": {
            "repository": "https://github.com/codernayeem/fruit-classification-dataset",
            "driveFolder": "https://drive.google.com/drive/folders/1g24PoWVzFZZ5G8QUJQuMFh3Cl5o2XU-c",
            "licenseClaim": "CC BY 4.0 (publisher claim; underlying online-image rights not independently verified)",
            "archive": source_archive.relative_to(project_root).as_posix(),
            "archiveSha256": sha256_file(source_archive),
        },
        "frozenManifest": frozen_manifest.relative_to(project_root).as_posix(),
        "counts": {
            "externalTotal": len(external),
            "externalByLabel": dict(sorted(Counter(str(row["sourceLabel"]) for row in external).items())),
            "frozenTotal": len(frozen),
            "crossDatasetMatchedRecords": len(excluded),
            "crossDatasetMatchPairs": len(matches),
            "internalDuplicatesRemoved": len(internal_removed),
            "safeIndependentRecords": len(safe),
            "safeByLabel": dict(sorted(Counter(str(row["sourceLabel"]) for row in safe).items())),
        },
        "crossDatasetMatches": matches,
        "internalRemovedExamples": [
            {key: value for key, value in row.items() if key in {"path", "sourceLabel", "sourceSplit", "reason"}}
            for row in internal_removed[:100]
        ],
        "safeRecords": safe,
        "rules": [
            "Every external record matching frozen evidence by bytes, decoded pixels, or conservative perceptual hashes is excluded.",
            "External near-duplicate groups retain one representative and cannot inflate pretraining counts.",
            "Good/medium/bad labels are not converted into Grade A/B/C/Reject labels.",
            "PitayaGrade train/validation data may fine-tune the pretrained backbone; the frozen test split remains evaluation-only.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result["counts"], indent=2))


if __name__ == "__main__":
    main()
