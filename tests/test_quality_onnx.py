import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class QualityOnnxExportTests(unittest.TestCase):
    def test_exports_checked_single_file_contract_without_overwriting(self):
        try:
            import onnx
            import torch
            from scripts.quality_onnx import export_quality_onnx
        except ImportError as error:
            self.skipTest(f'ONNX export dependencies are unavailable: {error}')

        class TinyQualityModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.classifier = torch.nn.Linear(3, 4)

            def forward(self, images):
                return self.classifier(images.mean(dim=(2, 3)))

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'quality.onnx'
            classes = ['Grade A', 'Grade B', 'Grade C', 'Reject']
            record = export_quality_onnx(TinyQualityModel(), output, classes)
            self.assertTrue(output.is_file())
            self.assertFalse(output.with_suffix('.onnx.data').exists())
            onnx.checker.check_model(onnx.load(str(output), load_external_data=False))
            self.assertEqual(record['inputShape'], [1, 3, 224, 224])
            self.assertEqual(record['outputShape'], [1, 4])
            self.assertEqual(len(record['sha256']), 64)
            saved = json.loads(output.with_suffix('.onnx.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['preprocessing'], 'rgb-imagenet-normalized')
            node = shutil.which('node')
            if node:
                root = Path(__file__).resolve().parents[1]
                checked = subprocess.run(
                    [node, str(root / 'scripts' / 'verify-model-candidate.js'),
                     'efficientnet-b3-quality', str(output)],
                    cwd=root, capture_output=True, text=True, check=False,
                )
                self.assertEqual(checked.returncode, 0, checked.stderr)
                runtime_record = json.loads(checked.stdout)
                self.assertEqual(runtime_record['outputShapes'], [[1, 4]])
                self.assertTrue(runtime_record['runtimeCompatible'])
            with self.assertRaises(FileExistsError):
                export_quality_onnx(TinyQualityModel(), output, classes)

    def test_rejects_incompatible_class_order(self):
        try:
            import torch
            from scripts.quality_onnx import export_quality_onnx
        except ImportError as error:
            self.skipTest(f'ONNX export dependencies are unavailable: {error}')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                export_quality_onnx(torch.nn.Identity(), Path(directory) / 'bad.onnx',
                                    ['Reject', 'Grade A', 'Grade B', 'Grade C'])

    def test_resnet_fine_tuning_unfreezes_only_upper_blocks(self):
        try:
            import torch
            import train_models
        except ImportError as error:
            self.skipTest(f'Training dependencies are unavailable: {error}')

        class SyntheticResNet(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.backbone = torch.nn.Module()
                self.backbone.stem = torch.nn.Linear(2, 2)
                self.backbone.layer4 = torch.nn.Sequential(*[torch.nn.Linear(2, 2) for _ in range(4)])
                self.classifier = torch.nn.Linear(2, 4)

        model = SyntheticResNet()
        train_models.unfreeze_backbone(model)
        self.assertTrue(all(not parameter.requires_grad for parameter in model.backbone.stem.parameters()))
        blocks = list(model.backbone.layer4.children())
        self.assertTrue(all(not parameter.requires_grad for parameter in blocks[0].parameters()))
        self.assertTrue(all(parameter.requires_grad for block in blocks[-3:] for parameter in block.parameters()))
