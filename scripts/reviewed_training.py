"""Prepare only reviewed manuscript grades, preserving approved partitions."""
import argparse
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

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
    args = parser.parse_args()
    try:
        for name in ('phase1_epochs', 'phase2_epochs', 'patience', 'batch_size'):
            if getattr(args, name) < 1:
                raise ValueError(f'--{name.replace("_", "-")} must be at least 1')
        if args.num_workers < 0:
            raise ValueError('--num-workers cannot be negative')
        args.rows = read_reviewed_manifest(args.manifest)
        if args.run_dir.exists():
            raise ValueError('Run directory already exists; choose a new directory.')
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return args
