"""Run separately with the pinned ML environment; all inputs are synthetic."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
from torch import nn
from PIL import Image, ImageDraw, ImageOps
from ultralytics import YOLO

import train_models as quality
from scripts.manuscript_yolo import ManuscriptDetectionTrainer, ManuscriptSegmentationTrainer


class TinyClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = nn.Module()
        self.backbone.features = nn.Sequential(nn.Conv2d(3, 3, 1), nn.BatchNorm2d(3),
                                              nn.ReLU(), nn.AdaptiveAvgPool2d(1), nn.Flatten())
        self.classifier = nn.Linear(3, 2)

    def forward(self, images):
        return self.classifier(self.backbone.features(images))


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def test_quality_checkpoint_prefers_loss_over_accuracy_and_last_epoch(self):
        model = TinyClassifier()
        counter = 0

        def epoch(model, loader, criterion, optimizer):
            nonlocal counter
            counter += 1
            self.assertTrue(all(g['weight_decay'] == 1e-4 for g in optimizer.param_groups))
            with torch.no_grad():
                model.classifier.bias.fill_(counter)
            return 1, 0.5

        with tempfile.TemporaryDirectory() as temp, patch.object(quality, 'RESULTS_DIR', Path(temp)), \
                patch.object(quality, 'PHASE1_EPOCHS', 2), patch.object(quality, 'PHASE2_EPOCHS', 2), \
                patch.object(quality, 'train_one_epoch', side_effect=epoch), \
                patch.object(quality, 'validate', side_effect=[(1, .5), (.8, .4), (.9, .8), (.85, .9)]):
            _, history = quality.train_model('Synthetic', model, [], [])
            self.assertEqual(history['best_epoch'], 2)
            self.assertEqual(history['best_val_loss'], .8)
            self.assertTrue(torch.equal(model.classifier.bias, torch.full((2,), 2.0)))
            saved = torch.load(Path(temp) / 'Synthetic_best.pth', weights_only=True)
            self.assertTrue(torch.equal(saved['classifier.bias'], model.classifier.bias))

    def test_frozen_backbone_preserves_batchnorm_statistics(self):
        model = TinyClassifier()
        quality.freeze_backbone(model)
        before = model.backbone.features[1].running_mean.clone()
        optimizer = torch.optim.Adam(model.classifier.parameters())
        inputs, labels = torch.randn(4, 3, 8, 8), torch.tensor([0, 1, 0, 1])
        quality.train_one_epoch(model, [(inputs, labels)], nn.CrossEntropyLoss(), optimizer)
        self.assertTrue(torch.equal(before, model.backbone.features[1].running_mean))

    def test_quality_loaders_orient_before_resizing_and_normalization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = Image.new('RGB', (12, 8), (20, 30, 40))
            ImageDraw.Draw(raw).rectangle((0, 0, 4, 2), fill=(220, 50, 80))
            exif = raw.getexif()
            exif[274] = 6
            for split in ('train', 'val', 'test'):
                folder = root / split / 'Grade A'
                folder.mkdir(parents=True)
                raw.save(folder / 'rotated.png', exif=exif)
            with patch.object(quality, 'NUM_WORKERS', 0):
                train, val, test, _ = quality.create_dataloaders(root)
                for loader in (train, val, test):
                    path = loader.dataset.samples[0][0]
                    actual = loader.dataset.loader(path)
                    self.assertEqual(actual.size, (8, 12))
                    with Image.open(path) as source:
                        expected = ImageOps.exif_transpose(source).convert('RGB')
                    self.assertEqual(actual.tobytes(), expected.tobytes())
                tensor, _ = next(iter(val))
                expected_tensor = val.dataset.transform(expected)
                self.assertEqual(tuple(tensor.shape), (1, 3, 224, 224))
                self.assertTrue(torch.equal(tensor[0], expected_tensor))
                self.assertTrue(torch.equal(test.dataset[0][0], expected_tensor))

    def test_real_efficientnet_head_backpropagates_with_frozen_features(self):
        factory = quality.models.efficientnet_b3
        with patch.object(quality.models, 'efficientnet_b3', side_effect=lambda **_: factory(weights=None)):
            model = quality.build_model('EfficientNetB3')
        quality.freeze_backbone(model)
        optimizer = torch.optim.Adam(model.classifier.parameters(), lr=.001, weight_decay=1e-4)
        loss, accuracy = quality.train_one_epoch(model, [(torch.randn(2, 3, 224, 224), torch.tensor([0, 1]))],
                                                nn.CrossEntropyLoss(), optimizer)
        self.assertTrue(torch.isfinite(torch.tensor(loss)))
        self.assertTrue(any(p.grad is not None for p in model.classifier.parameters()))
        self.assertTrue(all(p.grad is None for p in model.backbone.parameters()))
        quality.unfreeze_backbone(model)
        blocks = list(model.backbone.features.children())
        self.assertTrue(all(not p.requires_grad for block in blocks[:-3] for p in block.parameters()))
        self.assertTrue(all(p.requires_grad for block in blocks[-3:] for p in block.parameters()))

    def test_yolo_plateau_scheduler_and_loss_fitness(self):
        trainer = object.__new__(ManuscriptDetectionTrainer)
        trainer.optimizer = torch.optim.Adam([nn.Parameter(torch.ones(1))], lr=.001)
        trainer.best_fitness = None
        trainer._setup_scheduler()
        trainer.validator = lambda _: {'val/box_loss': 1, 'val/cls_loss': .5,
                                       'val/dfl_loss': .5, 'fitness': .99}
        for _ in range(7):
            trainer.scheduler.step()  # The base trainer's pre-epoch call must not reset LR.
            metrics, fitness = trainer.validate()
        self.assertEqual(fitness, -2)
        self.assertEqual(metrics['val/total_loss'], 2)
        self.assertEqual(trainer.optimizer.param_groups[0]['lr'], .0005)
        trainer.scheduler.step()
        self.assertEqual(trainer.optimizer.param_groups[0]['lr'], .0005)

    def test_yolo_rejects_missing_or_nonfinite_validation_loss(self):
        trainer = object.__new__(ManuscriptDetectionTrainer)
        for metrics in ({}, {'val/box_loss': float('nan'), 'val/cls_loss': 1, 'val/dfl_loss': 1}):
            trainer.validator = lambda _, value=metrics: value
            with self.assertRaises((ValueError, RuntimeError)):
                trainer.validate()

    def test_real_yolo_two_epoch_smoke(self):
        self._yolo_smoke(segmentation=False)

    def test_real_segmentation_two_epoch_smoke(self):
        self._yolo_smoke(segmentation=True)

    def test_segmentation_requires_and_monitors_mask_loss(self):
        trainer = object.__new__(ManuscriptSegmentationTrainer)
        trainer.optimizer = torch.optim.Adam([nn.Parameter(torch.ones(1))], lr=.001)
        trainer.best_fitness = None
        trainer._setup_scheduler()
        losses = {'val/box_loss': 1, 'val/cls_loss': .5, 'val/dfl_loss': .5,
                  'val/seg_loss': 2, 'val/sem_loss': 0, 'fitness': .99}
        trainer.validator = lambda _: dict(losses)
        _, fitness = trainer.validate()
        self.assertEqual(fitness, -4)
        losses['val/seg_loss'] = 3
        trainer.validate()
        self.assertEqual(trainer.best_fitness, -4)
        del losses['val/seg_loss']
        with self.assertRaisesRegex(RuntimeError, 'loss components'):
            trainer.validate()

    def _yolo_smoke(self, segmentation):
        with tempfile.TemporaryDirectory(prefix='pitaya-synthetic-') as temp:
            root = Path(temp)
            for split in ('train', 'val'):
                (root / 'images' / split).mkdir(parents=True)
                (root / 'labels' / split).mkdir(parents=True)
                for i in range(4):
                    image = Image.new('RGB', (64, 64), (20 + i * 5, 40, 20))
                    ImageDraw.Draw(image).rectangle((16, 16, 48, 48), fill=(180, 40 + i * 5, 80))
                    image.save(root / 'images' / split / f'{i}.png')
                    annotation = '0 0.25 0.25 0.75 0.25 0.75 0.75 0.25 0.75\n' if segmentation else '0 0.5 0.5 0.5 0.5\n'
                    (root / 'labels' / split / f'{i}.txt').write_text(annotation)
            config = root / 'data.yaml'
            config.write_text('path: ' + json.dumps(root.as_posix()) + '\ntrain: images/train\nval: images/val\nnames:\n  0: synthetic\n')
            model = YOLO('yolov8n-seg.yaml' if segmentation else 'yolov8n.yaml')  # Random initialization.
            trainer = ManuscriptSegmentationTrainer if segmentation else ManuscriptDetectionTrainer
            model.train(trainer=trainer, data=str(config), device='cpu',
                        project=str(root / 'runs'), name='smoke', epochs=2, imgsz=64,
                        batch=2, nbs=2, workers=0, optimizer='Adam', momentum=.9, lr0=.001, weight_decay=1e-4,
                        warmup_epochs=0, val=True, patience=10, pretrained=False,
                        plots=False, amp=False, mosaic=0, close_mosaic=0, verbose=False)
            checkpoint = root / 'runs' / 'smoke' / 'weights' / 'best.pt'
            self.assertTrue(checkpoint.is_file())
            record = torch.load(checkpoint, map_location='cpu', weights_only=False)
            self.assertIn('val/total_loss', record['train_metrics'])
            if segmentation:
                self.assertIn('val/seg_loss', record['train_metrics'])
            self.assertAlmostEqual(record['train_metrics']['fitness'], -record['train_metrics']['val/total_loss'])
            with (root / 'runs' / 'smoke' / 'results.csv').open() as stream:
                losses = [float(row['val/total_loss']) for row in csv.DictReader(stream)]
            self.assertAlmostEqual(record['train_metrics']['val/total_loss'], min(losses), places=4)


if __name__ == '__main__':
    unittest.main()
