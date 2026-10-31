"""Prepare only reviewed manuscript grades, preserving approved partitions."""
import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

from scripts.external_pretraining import read_external_pretraining_audit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('research_validation', Path(__file__).with_name('validate-research-data.py'))
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


def read_reviewed_manifest(manifest, root=ROOT):
    all_rows = json.loads(Path(manifest).read_text(encoding='utf-8'))
    if not isinstance(all_rows, list):
        raise ValueError('Reviewed manifest must be a JSON array')
    rows = [row for row in all_rows if row.get('task') == 'quality']
    if not rows:
        raise ValueError('Research data is not training-ready: reviewed manifest contains no quality records')
    errors = validation.validate(rows, 'manuscript-quality', root=root)
    if errors:
        raise ValueError(f'Research data is not training-ready ({len(errors)} errors):\n' + '\n'.join(errors[:20]))
    return rows


def prepare_reviewed_dataset(rows, run_dir, root=ROOT):
    # Recheck immediately before copying; never reuse legacy prepared data.
    errors = validation.validate(rows, 'manuscript-quality', root=root)
    if errors:
        raise ValueError('\n'.join(errors[:20]))
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    prepared = run_dir / 'dataset'
    for row in rows:
        source = root / row['image']
        name = hashlib.sha256(row['id'].encode()).hexdigest() + source.suffix.lower()
        destination = prepared / row['candidateSplit'] / row['reviewedLabel'] / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != row['fileSha256']:
            raise ValueError('Image changed during preparation')
    (run_dir / 'reviewed-manifest.json').write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    return prepared


def prepared_sample_ids(rows, samples):
    """Recover manifest IDs from the hashed filenames emitted during preparation."""
    identifiers = {
        hashlib.sha256(row['id'].encode()).hexdigest(): row['id']
        for row in rows if row.get('task') == 'quality' and row.get('candidateSplit') == 'test'
    }
    ordered = []
    for sample in samples:
        path = Path(sample[0] if isinstance(sample, (tuple, list)) else sample)
        ident = identifiers.get(path.stem)
        if not ident:
            raise ValueError(f'Prepared test image has no reviewed-manifest identity: {path.name}')
        ordered.append(ident)
    if len(ordered) != len(set(ordered)) or set(ordered) != set(identifiers.values()):
        raise ValueError('Prepared test samples do not match the frozen reviewed manifest exactly')
    return ordered


def write_prediction_csv(path, model_id, sample_ids, predicted_labels, confidences, inference_ms):
    lengths = {len(sample_ids), len(predicted_labels), len(confidences), len(inference_ms)}
    if len(lengths) != 1 or not sample_ids:
        raise ValueError('Prediction evidence must contain one complete row per test sample')
    path = Path(path)
    with path.open('x', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            'model_id', 'sample_id', 'predicted_label', 'confidence', 'inference_ms'])
        writer.writeheader()
        for values in zip(sample_ids, predicted_labels, confidences, inference_ms):
            sample_id, predicted_label, confidence, latency = values
            writer.writerow({'model_id': model_id, 'sample_id': sample_id,
                             'predicted_label': predicted_label,
                             'confidence': f'{float(confidence):.10f}',
                             'inference_ms': f'{float(latency):.6f}'})
    return path


def training_arguments():
    parser = argparse.ArgumentParser(description='Train selectable quality models using reviewed grade labels and source-group partitions.')
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--run-dir', required=True, type=Path, help='New directory; existing results are never overwritten or resumed.')
    parser.add_argument('--models', nargs='+', choices=['MobileNetV2', 'ResNet50', 'EfficientNetB3'],
                        default=['MobileNetV2', 'ResNet50', 'EfficientNetB3'],
                        help='Quality architectures to train; defaults to all selectable classifiers.')
    parser.add_argument('--phase1-epochs', type=int, default=10,
                        help='Frozen-backbone epochs (default: 10).')
    parser.add_argument('--phase2-epochs', type=int, default=30,
                        help='Fine-tuning epochs (default: 30).')
    parser.add_argument('--patience', type=int, default=10,
                        help='Early-stopping patience in epochs (default: 10).')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='Training batch size (default: 32).')
    parser.add_argument('--num-workers', type=int, default=2,
                        help='Data-loader worker processes (default: 2; use 0 for maximum Windows reliability).')
    parser.add_argument('--external-pretraining-audit', type=Path,
                        help='Optional leakage-audited good/medium feature-pretraining evidence.')
    parser.add_argument('--external-pretrain-epochs', type=int, default=12,
                        help='Maximum good/medium feature-pretraining epochs (default: 12).')
    parser.add_argument('--external-pretrain-patience', type=int, default=4,
                        help='Feature-pretraining early-stopping patience (default: 4).')
    args = parser.parse_args()
    try:
        for name in ('phase1_epochs', 'phase2_epochs', 'patience', 'batch_size',
                     'external_pretrain_epochs', 'external_pretrain_patience'):
            if getattr(args, name) < 1:
                raise ValueError(f'--{name.replace("_", "-")} must be at least 1')
        if args.num_workers < 0:
            raise ValueError('--num-workers cannot be negative')
        args.rows = read_reviewed_manifest(args.manifest)
        if args.run_dir.exists():
            raise ValueError('Run directory already exists; choose a new directory.')
        args.external_audit = None
        if args.external_pretraining_audit:
            args.external_audit = read_external_pretraining_audit(
                args.external_pretraining_audit, args.manifest, ROOT)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return args
