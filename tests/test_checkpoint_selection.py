import tempfile
import unittest
from pathlib import Path
from scripts.training_policy import best_phase_checkpoint


class CheckpointSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for phase in ('phase1', 'phase2'):
            weights = self.root / phase / 'weights'
            weights.mkdir(parents=True)
            (weights / 'best.pt').write_bytes(b'synthetic')

    def history(self, phase, losses):
        (self.root / phase / 'results.csv').write_text('epoch,val/total_loss\n' +
            ''.join(f'{i + 1},{loss}\n' for i, loss in enumerate(losses)))

    def test_worse_fine_tuning_keeps_phase_one(self):
        self.history('phase1', [3, 1, 2])
        self.history('phase2', [4, 2])
        selected, record = best_phase_checkpoint(self.root)
        self.assertEqual(selected, self.root / 'phase1/weights/best.pt')
        self.assertEqual(record['selectedPhase'], 'phase1')

    def test_better_fine_tuning_wins_and_ties_keep_phase_one(self):
        self.history('phase1', [3, 2])
        self.history('phase2', [4, 1])
        self.assertEqual(best_phase_checkpoint(self.root)[1]['selectedPhase'], 'phase2')
        self.history('phase2', [2])
        self.assertEqual(best_phase_checkpoint(self.root)[1]['selectedPhase'], 'phase1')

    def test_missing_or_bad_history_cannot_select_or_consult_test_metrics(self):
        self.history('phase1', [2])
        (self.root / 'test-metrics.json').write_text('{"accuracy":1}')
        for losses in ([], ['nan'], ['inf'], [-1], ['invalid']):
            self.history('phase2', losses)
            with self.subTest(losses=losses), self.assertRaises(ValueError):
                best_phase_checkpoint(self.root)
