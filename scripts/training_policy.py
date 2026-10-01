"""Validation-loss policy shared by the manuscript training workflows."""
import math
import csv
from pathlib import Path


def best_phase_checkpoint(run_dir):
    """Select between frozen/fine-tuned checkpoints using validation only."""
    candidates = []
    for phase in ('phase1', 'phase2'):
        folder = Path(run_dir) / phase
        checkpoint = folder / 'weights' / 'best.pt'
        if not checkpoint.is_file():
            raise ValueError(f'{phase}: missing best checkpoint')
        with (folder / 'results.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream, skipinitialspace=True))
        if not rows:
            raise ValueError(f'{phase}: missing validation history')
        losses = []
        for row in rows:
            try:
                value = float(row['val/total_loss'])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f'{phase}: missing or invalid validation total loss') from error
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'{phase}: validation loss must be finite and nonnegative')
            losses.append(value)
        candidates.append({'phase': phase, 'validationLoss': min(losses),
                           'checkpoint': checkpoint.relative_to(run_dir).as_posix()})
    winner = min(candidates, key=lambda candidate: candidate['validationLoss'])
    return Path(run_dir) / winner['checkpoint'], {'selectedPhase': winner['phase'],
        'selectionMetric': 'minimum validation total loss across both phases',
        'tiePolicy': 'retain phase1', 'candidates': candidates}


class LossMonitor:
    def __init__(self, patience=10):
        self.patience = patience
        self.best = float('inf')
        self.bad_epochs = 0
        self.best_epoch = None

    def update(self, loss, epoch):
        loss = float(loss)
        if not math.isfinite(loss) or loss < 0:
            raise ValueError('Validation loss must be finite and nonnegative')
        improved = loss < self.best
        if improved:
            self.best, self.best_epoch, self.bad_epochs = loss, epoch, 0
        else:
            self.bad_epochs += 1
        return improved

    @property
    def should_stop(self):
        return self.bad_epochs >= self.patience


class LossEarlyStopping:
    """Ultralytics expects larger fitness; our trainer returns negative loss."""
    def __init__(self, patience=10):
        self.monitor = LossMonitor(patience)
        self.possible_stop = False

    def __call__(self, epoch, fitness):
        self.monitor.update(-float(fitness), epoch)
        self.possible_stop = self.monitor.bad_epochs >= self.monitor.patience - 1
        return self.monitor.should_stop
