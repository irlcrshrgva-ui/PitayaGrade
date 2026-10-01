"""Reviewed YOLOv8-Nano fruit localization, separate from quality grading.

Requires genuine annotations; never invents centered boxes. Outputs are research
artifacts and are incompatible with the deployed four-grade detector contract.
See research/PREPARATION_GUIDE.md before training or integration.
"""
import json
from pathlib import Path

from scripts.reviewed_detection import detection_arguments, prepare_detection_dataset
from scripts.training_policy import best_phase_checkpoint
import hashlib


def train_detector(data_yaml, run_dir, yolo_factory, device, trainer_class, *, initial_weights='yolov8n.pt'):
    """Train both phases before consulting the held-out test split."""
    run_dir = Path(run_dir).resolve()
    common = dict(data=str(data_yaml), imgsz=128, batch=32, patience=10,
                  workers=2, seed=42, device=device, project=str(run_dir),
                  exist_ok=False, optimizer='Adam', momentum=0.9, lr0=1e-3, lrf=1.0,
                  weight_decay=1e-4, warmup_epochs=0, cos_lr=False,
                  save=True, plots=True, verbose=True, val=True, trainer=trainer_class)
    phase1 = yolo_factory(initial_weights)
    phase1.train(**common, name='phase1', epochs=10, freeze=10)
    phase1_best = run_dir / 'phase1' / 'weights' / 'best.pt'
    if not phase1_best.is_file():
        raise RuntimeError('Phase 1 did not produce a best checkpoint')
    phase2 = yolo_factory(str(phase1_best))
    common['lr0'] = 1e-5
    phase2.train(**common, name='phase2', epochs=30, freeze=5)
    best = run_dir / 'phase2' / 'weights' / 'best.pt'
    if not best.is_file():
        raise RuntimeError('Phase 2 did not produce a best checkpoint')
    best, selection = best_phase_checkpoint(run_dir)
    selection['checkpointSha256'] = hashlib.sha256(best.read_bytes()).hexdigest()
    (run_dir / 'checkpoint-selection.json').write_text(json.dumps(selection, indent=2) + '\n', encoding='utf-8')
    final_model = yolo_factory(str(best))
    metrics = final_model.val(data=str(data_yaml), split='test', imgsz=128,
                              device=device, project=str(run_dir),
                              name='test_eval', exist_ok=False)
    (run_dir / 'test-metrics.json').write_text(
        json.dumps(metrics.results_dict, indent=2) + '\n', encoding='utf-8')
    return best


def main(argv=None):
    args = detection_arguments(argv)
    # Preparation remains usable without Ultralytics or a GPU.
    if not args.prepare_only:
        import torch
        import ultralytics
        from ultralytics import YOLO
        from scripts.manuscript_yolo import ManuscriptDetectionTrainer
    data_yaml = prepare_detection_dataset(args.rows, args.run_dir)
    print(f'Reviewed detection dataset: {data_yaml}')
    if args.prepare_only:
        print('Preparation only; no model trained and no accuracy established.')
        return
    run_dir = args.run_dir.resolve()
    (run_dir / 'training-context.json').write_text(json.dumps({
        'task': 'fruit-localization-only', 'classes': ['Dragon Fruit'],
        'torch': torch.__version__, 'ultralytics': ultralytics.__version__,
        'phase1': {'epochs': 10, 'freeze': 10, 'lr0': 0.001},
        'phase2': {'epochs': 30, 'freeze': 5, 'lr0': 0.00001},
        'imageSize': 128, 'batchSize': 32, 'seed': 42,
        'selectionMetric': 'sum of val/box_loss, val/cls_loss, val/dfl_loss',
        'scheduler': {'name': 'ReduceLROnPlateau', 'patience': 5, 'factor': 0.5},
        'earlyStopping': {'monitor': 'val/total_loss', 'patience': 10},
        'methodologyLimitations': [
            'Disease segmentation, independent field evaluation and app integration remain outstanding.'
        ]
    }, indent=2) + '\n', encoding='utf-8')
    best = train_detector(data_yaml, run_dir, YOLO, 0 if torch.cuda.is_available() else 'cpu',
                          ManuscriptDetectionTrainer)
    print(f'Research checkpoint: {best}')
    print('Do not replace the deployed four-grade model with this one-class detector.')


if __name__ == '__main__':
    main()
