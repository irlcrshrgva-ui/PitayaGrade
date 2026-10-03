"""Export the retained four-grade PyTorch model as a single-file ONNX candidate."""
import hashlib
import json
from pathlib import Path


def export_quality_onnx(model, output_path, class_names, input_size=224):
    import onnx
    import torch

    output_path = Path(output_path)
    metadata_path = output_path.with_suffix(output_path.suffix + '.json')
    if output_path.exists() or metadata_path.exists():
        raise FileExistsError('Refusing to overwrite an existing ONNX export')
    if list(class_names) != ['Grade A', 'Grade B', 'Grade C', 'Reject']:
        raise ValueError('ONNX class order must match the app registry')
    if input_size != 224:
        raise ValueError('Quality ONNX input must match the 224px training contract')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model = model.eval().cpu()
    sample = torch.zeros(1, 3, input_size, input_size, dtype=torch.float32)
    torch.onnx.export(
        model,
        (sample,),
        output_path,
        input_names=['images'],
        output_names=['grade_logits'],
        opset_version=18,
        dynamo=True,
        external_data=False,
        verbose=False,
    )
    exported = onnx.load(str(output_path), load_external_data=False)
    onnx.checker.check_model(exported)
    if len(exported.graph.input) != 1 or len(exported.graph.output) != 1:
        raise ValueError('Quality export must have exactly one input and one output')

    record = {
        'format': 'ONNX',
        'opset': 18,
        'inputName': 'images',
        'inputShape': [1, 3, input_size, input_size],
        'preprocessing': 'rgb-imagenet-normalized',
        'outputName': 'grade_logits',
        'outputShape': [1, len(class_names)],
        'outputContract': 'quality-softmax-v1',
        'classes': list(class_names),
        'sha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
        'runtimeVerificationRequired': True,
        'accuracyValidatedByExport': False,
    }
    metadata_path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record
