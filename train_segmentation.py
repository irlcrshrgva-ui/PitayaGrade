"""Manuscript symptom segmentation from genuine reviewed fruit-ROI polygons."""
import json
from scripts.reviewed_segmentation import SYMPTOMS, segmentation_arguments, prepare_segmentation_dataset
from train_yolo import train_detector


def main(argv=None):
    args = segmentation_arguments(argv)
    if not args.prepare_only:
        import torch
        import ultralytics
        from ultralytics import YOLO
        from scripts.manuscript_yolo import ManuscriptSegmentationTrainer
    data_yaml = prepare_segmentation_dataset(args.rows, args.run_dir)
    print(f'Reviewed symptom dataset: {data_yaml}')
    if args.prepare_only:
        print('Preparation only; no accuracy established and no model trained.')
        return
    context = {
        'task': 'symptom-segmentation', 'model': 'yolov8n-seg', 'classes': list(SYMPTOMS),
        'healthyRepresentation': 'reviewed negative ROI with no symptom polygons; not an inferred diagnosis',
        'torch': torch.__version__, 'ultralytics': ultralytics.__version__,
        'imageSize': 128, 'batchSize': 32, 'seed': 42,
        'phases': [{'epochs': 10, 'freeze': 10, 'lr': .001}, {'epochs': 30, 'freeze': 5, 'lr': .00001}],
        'selectionMetric': 'sum of validation box, mask, class, DFL and semantic losses',
        'scheduler': {'name': 'ReduceLROnPlateau', 'patience': 5, 'factor': .5},
        'earlyStopping': {'monitor': 'val/total_loss', 'patience': 10},
        'limitations': ['Review metadata cannot establish label truth or crop provenance.',
                        'Full preprocessing, field evaluation, coverage denominator and app integration remain unfinished.']
    }
    (args.run_dir / 'training-context.json').write_text(json.dumps(context, indent=2) + '\n', encoding='utf-8')
    best = train_detector(data_yaml, args.run_dir, YOLO, 0 if torch.cuda.is_available() else 'cpu',
                          ManuscriptSegmentationTrainer, initial_weights='yolov8n-seg.pt')
    print(f'Research checkpoint: {best}. Not exported or integrated into the app.')


if __name__ == '__main__':
    main()
