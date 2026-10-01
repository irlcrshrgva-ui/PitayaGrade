import unittest
from scripts.training_policy import LossMonitor, LossEarlyStopping


class PolicyTests(unittest.TestCase):
    def test_lower_loss_selects_checkpoint(self):
        monitor = LossMonitor()
        self.assertTrue(monitor.update(1.0, 1))
        self.assertTrue(monitor.update(0.8, 2))
        self.assertFalse(monitor.update(0.9, 3))
        self.assertEqual(monitor.best_epoch, 2)

    def test_ties_count_toward_patience(self):
        monitor = LossMonitor(patience=2)
        monitor.update(1.0, 1)
        monitor.update(1.0, 2)
        self.assertFalse(monitor.should_stop)
        monitor.update(1.0, 3)
        self.assertTrue(monitor.should_stop)

    def test_improvement_resets_patience(self):
        monitor = LossMonitor(patience=2)
        for epoch, loss in enumerate((1, 1, 0.9, 0.9)):
            monitor.update(loss, epoch)
        self.assertEqual(monitor.bad_epochs, 1)
        self.assertFalse(monitor.should_stop)

    def test_nonfinite_values_cannot_select_a_checkpoint(self):
        for loss in (float('nan'), float('inf'), -1):
            with self.assertRaises(ValueError):
                LossMonitor().update(loss, 1)

    def test_negative_fitness_adapter(self):
        stopper = LossEarlyStopping(2)
        self.assertFalse(stopper(1, -1))
        self.assertFalse(stopper(2, -1.1))
        self.assertTrue(stopper.possible_stop)
        self.assertTrue(stopper(3, -1.2))
