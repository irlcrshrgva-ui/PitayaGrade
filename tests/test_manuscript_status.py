import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ManuscriptStatusTests(unittest.TestCase):
    def test_manuscript_does_not_present_unverified_results_as_findings(self):
        text = (ROOT / 'PitayaGrade_Capstone_Paper.md').read_text(encoding='utf-8')
        self.assertIn('Evidence status (4 October 2026)', text)
        self.assertIn('Do not cite the numerical tables in this chapter as results', text)
        self.assertIn('local ONNX Runtime Web inference', text)
        forbidden = [
            'Experimental evaluation demonstrates that the system achieves',
            'User acceptance testing (UAT) was conducted with 15 participants',
            'Testing was conducted over a four-week period from October to November 2025',
            'successfully designed, developed, and evaluated **PitayaGrade**',
            'The overall accuracy of the quality grading model on the test set was **94.3%**',
            'The overall accuracy of the disease detection model on the test set was **91.7%**',
        ]
        for claim in forbidden:
            self.assertNotIn(claim, text)


if __name__ == '__main__':
    unittest.main()

