"""Version-tested Ultralytics adaptation for manuscript validation-loss policy."""
import math

import ultralytics
from torch.optim.lr_scheduler import ReduceLROnPlateau
from ultralytics.models.yolo.detect import DetectionTrainer
from ultralytics.models.yolo.segment import SegmentationTrainer

from scripts.training_policy import LossEarlyStopping

TESTED_ULTRALYTICS = '8.4.156'


class ValidationPlateau(ReduceLROnPlateau):
    # The base trainer calls step() before an epoch. Only validation may change LR.
    def step(self, metrics=None, epoch=None):
        if metrics is not None:
            super().step(metrics, epoch)


class ValidationLossTrainerMixin:
    loss_keys = ('val/box_loss', 'val/cls_loss', 'val/dfl_loss')

    def __init__(self, *args, **kwargs):
        if ultralytics.__version__ != TESTED_ULTRALYTICS:
            raise RuntimeError(f'This training adapter requires ultralytics=={TESTED_ULTRALYTICS}')
        super().__init__(*args, **kwargs)
        if self.world_size > 1 or self.args.resume or self.args.time or not self.args.val:
            raise ValueError('Use a new single-device run with validation each epoch')
        if self.args.warmup_epochs:
            raise ValueError('Warmup must be disabled for validation-controlled learning rates')

    def _setup_scheduler(self):
        self.lf = lambda epoch: 1.0
        self.scheduler = ValidationPlateau(self.optimizer, mode='min', factor=0.5,
                                           patience=5, threshold=0, min_lr=1e-7)

    def _setup_train(self):
        super()._setup_train()
        self.stopper = LossEarlyStopping(self.args.patience)

    def validate(self):
        metrics = self.validator(self)
        keys = self.loss_keys
        if not isinstance(metrics, dict) or any(key not in metrics for key in keys):
            raise RuntimeError('Validation did not return all required loss components')
        values = [float(metrics[key]) for key in keys]
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError('Validation loss must be finite and nonnegative')
        loss = sum(values)
        metrics.pop('fitness', None)
        metrics['val/total_loss'] = loss
        fitness = -loss
        if self.best_fitness is None or fitness > self.best_fitness:
            self.best_fitness = fitness
        self.scheduler.step(loss)
        return metrics, fitness


class ManuscriptDetectionTrainer(ValidationLossTrainerMixin, DetectionTrainer):
    pass


class ManuscriptSegmentationTrainer(ValidationLossTrainerMixin, SegmentationTrainer):
    loss_keys = ('val/box_loss', 'val/seg_loss', 'val/cls_loss', 'val/dfl_loss', 'val/sem_loss')
