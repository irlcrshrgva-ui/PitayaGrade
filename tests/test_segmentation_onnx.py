import json
import shutil
import tempfile
import unittest
from pathlib import Path


class SegmentationOnnxExportTests(unittest.TestCase):
    def _template(self, path, *, channels=42):
        import onnx
        from onnx import TensorProto, helper

        image = helper.make_tensor_value_info('images', TensorProto.FLOAT, [1, 3, 128, 128])
        detections = helper.make_tensor_value_info('detections', TensorProto.FLOAT, [1, channels, 336])
        prototypes = helper.make_tensor_value_info('prototypes', TensorProto.FLOAT, [1, 32, 32, 32])
        detection_data = helper.make_tensor('detection_data', TensorProto.FLOAT,
                                            [1, channels, 336], [0.0] * (channels * 336))
        prototype_data = helper.make_tensor('prototype_data', TensorProto.FLOAT,
                                            [1, 32, 32, 32], [0.0] * (32 * 32 * 32))
        graph = helper.make_graph(
            [helper.make_node('Identity', ['detection_data'], ['detections']),
             helper.make_node('Identity', ['prototype_data'], ['prototypes'])],
            'synthetic-segmenter', [image], [detections, prototypes],
            initializer=[detection_data, prototype_data],
        )
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 18)])
        onnx.save(model, path)

    def test_exports_checked_six_class_single_file_contract(self):
        try:
            import onnx  # noqa: F401
            from scripts.segmentation_onnx import DISEASE_CLASSES, export_segmentation_onnx
        except ImportError as error:
            self.skipTest(f'ONNX export dependencies are unavailable: {error}')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root / 'best.pt'
            checkpoint.write_bytes(b'synthetic checkpoint')
            template = root / 'template.onnx'
            self._template(template)

            class FakeModel:
                def export(self, **options):
                    self.options = options
                    exported = Path(self.checkpoint).with_suffix('.onnx')
                    shutil.copy2(template, exported)
                    return exported

            models = []

            def factory(path):
                model = FakeModel()
                model.checkpoint = path
                models.append(model)
                return model

            output = root / 'candidate' / 'disease.onnx'
            record = export_segmentation_onnx(checkpoint, output, factory)
            self.assertTrue(output.is_file())
            self.assertFalse(output.with_suffix('.onnx.data').exists())
            self.assertEqual(record['classes'], DISEASE_CLASSES)
            self.assertNotIn('Healthy', record['classes'])
            self.assertEqual(record['inputShape'], [1, 3, 128, 128])
            self.assertEqual(record['outputShapes'], [[1, 42, 336], [1, 32, 32, 32]])
            self.assertEqual(len(record['sha256']), 64)
            saved = json.loads(output.with_suffix('.onnx.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['outputContract'], 'yolov8-disease-segmentation-v1')
            self.assertEqual(models[0].options['imgsz'], 128)
            self.assertFalse(models[0].options['dynamic'])
            with self.assertRaises(FileExistsError):
                export_segmentation_onnx(checkpoint, output, factory)

    def test_rejects_incompatible_output_and_class_order(self):
        try:
            from scripts.segmentation_onnx import export_segmentation_onnx
        except ImportError as error:
            self.skipTest(f'ONNX export dependencies are unavailable: {error}')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root / 'best.pt'
            checkpoint.write_bytes(b'synthetic checkpoint')
            template = root / 'bad.onnx'
            self._template(template, channels=43)

            class FakeModel:
                def export(self, **_):
                    exported = Path(self.checkpoint).with_suffix('.onnx')
                    shutil.copy2(template, exported)
                    return exported

            def factory(path):
                model = FakeModel()
                model.checkpoint = path
                return model

            with self.assertRaisesRegex(ValueError, 'detection shape'):
                export_segmentation_onnx(checkpoint, root / 'bad-output.onnx', factory)
            with self.assertRaisesRegex(ValueError, 'class order'):
                export_segmentation_onnx(checkpoint, root / 'bad-order.onnx', factory,
                                         ['Healthy', 'Anthracnose'])


if __name__ == '__main__':
    unittest.main()
