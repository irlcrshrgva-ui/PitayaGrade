"""Export a reviewed YOLO disease segmenter as a checked ONNX candidate."""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path


DISEASE_CLASSES = ['Anthracnose', 'Stem Canker', 'Soft Rot',
                   'Pest Damage', 'Sunburn', 'Fungal Spots']


def _shape(value):
    dimensions = value.type.tensor_type.shape.dim
    return [dimension.dim_value if dimension.HasField('dim_value') else None
            for dimension in dimensions]


def export_segmentation_onnx(checkpoint, output_path, yolo_factory,
                             class_names=DISEASE_CLASSES, input_size=128):
    """Export through Ultralytics, then reject files that do not match the app contract."""
    import onnx

    checkpoint = Path(checkpoint).resolve()
    output_path = Path(output_path).resolve()
    metadata_path = output_path.with_suffix(output_path.suffix + '.json')
    if not checkpoint.is_file():
        raise FileNotFoundError(f'Missing segmentation checkpoint: {checkpoint}')
    if output_path.exists() or metadata_path.exists():
        raise FileExistsError('Refusing to overwrite an existing ONNX export')
    if list(class_names) != DISEASE_CLASSES:
        raise ValueError('Segmentation ONNX class order must match the app registry')
    if input_size != 128:
        raise ValueError('Segmentation ONNX input must match the 128px training contract')

    with tempfile.TemporaryDirectory(prefix='pitaya-seg-export-') as temporary:
        temporary_checkpoint = Path(temporary) / 'segmenter.pt'
        shutil.copy2(checkpoint, temporary_checkpoint)
        exported_path = Path(yolo_factory(str(temporary_checkpoint)).export(
            format='onnx', imgsz=input_size, opset=18, dynamic=False,
            simplify=False, nms=False, batch=1,
        )).resolve()
        if not exported_path.is_file():
            raise RuntimeError('Ultralytics did not produce an ONNX file')
        exported = onnx.load(str(exported_path), load_external_data=False)
        onnx.checker.check_model(exported)
        opset = next((item.version for item in exported.opset_import
                      if item.domain in ('', 'ai.onnx')), None)
        if opset != 18:
            raise ValueError(f'Unexpected segmentation ONNX opset: {opset}')
        if len(exported.graph.input) != 1 or len(exported.graph.output) != 2:
            raise ValueError('Segmentation export must have one input and two outputs')
        input_shape = _shape(exported.graph.input[0])
        output_shapes = [_shape(value) for value in exported.graph.output]
        prototypes = next((shape for shape in output_shapes
                           if len(shape) == 4 and shape[0] == 1), None)
        detections = next((shape for shape in output_shapes
                           if len(shape) == 3 and shape[0] == 1), None)
        if input_shape != [1, 3, input_size, input_size]:
            raise ValueError(f'Unexpected segmentation input shape: {input_shape}')
        if not prototypes or not detections or not all(isinstance(value, int) and value > 0
                                                       for value in prototypes[1:]):
            raise ValueError(f'Unexpected segmentation outputs: {output_shapes}')
        expected_channels = 4 + len(class_names) + prototypes[1]
        if detections[1] != expected_channels or not isinstance(detections[2], int) or detections[2] < 1:
            raise ValueError(f'Unexpected segmentation detection shape: {detections}')
        if any(initializer.data_location == onnx.TensorProto.EXTERNAL
               for initializer in exported.graph.initializer):
            raise ValueError('Segmentation export must be a single-file ONNX model')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(exported_path, output_path)

    record = {
        'format': 'ONNX',
        'opset': opset,
        'inputName': exported.graph.input[0].name,
        'inputShape': input_shape,
        'preprocessing': 'rgb-zero-to-one',
        'outputNames': [value.name for value in exported.graph.output],
        'outputShapes': output_shapes,
        'outputContract': 'yolov8-disease-segmentation-v1',
        'classes': list(class_names),
        'healthyRepresentation': 'reviewed negative sample with no symptom mask; not an output class',
        'sha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
        'runtimeVerificationRequired': True,
        'accuracyValidatedByExport': False,
    }
    metadata_path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record
