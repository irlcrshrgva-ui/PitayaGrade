"""Train an experimental frozen MobileNetV3-small disease-label classifier on CPU."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import platform
from datetime import datetime, timezone

import numpy as np
from PIL import Image, ImageOps
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from sklearn.metrics import classification_report, confusion_matrix

from scripts.mendeley_disease import file_hash

SIZE = 160


def preprocessing():
    return transforms.Compose([transforms.Resize((SIZE, SIZE)), transforms.ToTensor(),
                               transforms.Normalize([.485, .456, .406], [.229, .224, .225])])


class Images(Dataset):
    def __init__(self, rows, root, classes):
        self.rows, self.root, self.classes = rows, root, classes
        self.transform = preprocessing()

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        with Image.open(self.root / row['path']) as image:
            tensor = self.transform(ImageOps.exif_transpose(image).convert('RGB'))
        return tensor, self.classes.index(row['label'])


def validate_manifest(manifest, verify_files=True):
    rows = manifest['rows']
    if not rows or {r['split'] for r in rows} != {'train', 'validation', 'test'}:
        raise ValueError('Require nonempty train/validation/test partitions')
    for key in ('group', 'sha256', 'pixelSha256'):
        seen = {}
        for row in rows:
            if row[key] in seen:
                raise ValueError('Duplicate or leaking ' + key)
            seen[row[key]] = row['split']
    classes = sorted({r['label'] for r in rows})
    for split in ('train', 'validation', 'test'):
        if {r['label'] for r in rows if r['split'] == split} != set(classes):
            raise ValueError('Every class must occur in each partition')
    root = Path(manifest['root']).resolve()
    for row in rows:
        path = (root / row['path']).resolve()
        if not path.is_relative_to(root) or (verify_files and file_hash(path) != row['sha256']):
            raise ValueError('Invalid path or modified image')
    return classes


def train(manifest_path, run_dir, epochs=40, task='disease'):
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    validate_manifest(manifest, verify_files=False)
    manifest['rows'] = [r for r in manifest['rows'] if r['task'] == task]
    if not manifest['rows']:
        raise ValueError('No images for selected task')
    classes = validate_manifest(manifest)
    run_dir.mkdir(parents=True, exist_ok=False)
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(4)
    torch.hub.set_dir(Path(manifest['root']) / 'pretrained-cache')
    started = datetime.now(timezone.utc).isoformat()
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT).eval()
    model.classifier = nn.Identity()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    features, targets = {}, {}
    for split in ('train', 'validation', 'test'):
        rows = [r for r in manifest['rows'] if r['split'] == split]
        loader = DataLoader(Images(rows, Path(manifest['root']), classes), batch_size=48, num_workers=0)
        values, labels = [], []
        with torch.inference_mode():
            for index, (images, truth) in enumerate(loader):
                values.append(model(images))
                labels.append(truth)
                if index % 10 == 0:
                    print(f'{split}: encoded {min((index+1)*48, len(rows))}/{len(rows)}', flush=True)
        features[split], targets[split] = torch.cat(values).clone(), torch.cat(labels)
    head = nn.Linear(576, len(classes))
    optimizer = torch.optim.AdamW(head.parameters(), lr=.003, weight_decay=.01)
    counts = torch.bincount(targets['train'], minlength=len(classes))
    weights = counts.sum() / (len(classes) * counts.float())
    criterion = nn.CrossEntropyLoss(weight=weights)
    best_loss, best_state, best_epoch = float('inf'), None, None
    history = []
    for epoch in range(epochs):
        head.train()
        order = torch.randperm(len(targets['train']))
        for indices in order.split(128):
            optimizer.zero_grad()
            loss = criterion(head(features['train'][indices]), targets['train'][indices])
            loss.backward()
            optimizer.step()
        head.eval()
        with torch.no_grad():
            logits = head(features['validation'])
            val_loss = nn.functional.cross_entropy(logits, targets['validation']).item()
            accuracy = (logits.argmax(1) == targets['validation']).float().mean().item()
        history.append({'epoch': epoch + 1, 'validationLoss': val_loss, 'validationAccuracy': accuracy})
        if val_loss < best_loss:
            best_loss, best_state, best_epoch = val_loss, copy.deepcopy(head.state_dict()), epoch + 1
        print(f'epoch {epoch+1}: validation loss {val_loss:.4f}, accuracy {accuracy:.4f}', flush=True)
    head.load_state_dict(best_state)
    head.eval()
    report = {'status': 'experimental-evaluated-image-classifier', 'task': task, 'classes': classes,
              'architecture': 'ImageNet MobileNetV3-small frozen encoder + trained linear head',
              'preprocessing': {'size': SIZE, 'resize': 'bilinear stretch', 'orientation': 'EXIF upright RGB',
                                'mean': [.485, .456, .406], 'std': [.229, .224, .225]},
              'manifestSha256': hashlib.sha256(raw).hexdigest(), 'seed': 42, 'epochs': epochs,
              'startedAtUtc': started, 'python': platform.python_version(), 'torch': torch.__version__,
              'device': 'cpu', 'threads': 4, 'trainingImages': len(targets['train']),
              'trainingClassCounts': dict(zip(classes, counts.tolist())),
              'optimizer': {'name': 'AdamW', 'learningRate': .003, 'weightDecay': .01, 'batchSize': 128},
              'augmentation': 'none; publisher augmentation excluded',
              'selectedEpoch': best_epoch, 'selectionMetric': 'minimum validation cross-entropy',
              'history': history, 'limitations': manifest['limitations'] + [
                  'Experimental source-label prediction, not a validated field diagnosis.',
                  'No lesion masks, affected-area estimates, quality grades, or treatment recommendations.',
                  'Softmax scores are uncalibrated; no out-of-distribution rejection was validated.']}
    with torch.no_grad():
        for split in ('validation', 'test'):
            predicted = head(features[split]).argmax(1).numpy()
            truth = targets[split].numpy()
            report[split] = {'count': len(truth), 'metrics': classification_report(
                truth, predicted, labels=list(range(len(classes))), target_names=classes,
                output_dict=True, zero_division=0), 'confusionMatrix': confusion_matrix(
                    truth, predicted, labels=list(range(len(classes)))).tolist()}
    model.classifier = head
    model.eval()
    torch.save({'state_dict': model.state_dict(), 'classes': classes}, run_dir / 'classifier.pth')
    # Compare exported inference on a real held-out image as well as using it as export input.
    sample = next(r for r in manifest['rows'] if r['split'] == 'test')
    example = Images([sample], Path(manifest['root']), classes)[0][0].unsqueeze(0)
    torch.onnx.export(model, example, str(run_dir / 'classifier.onnx'), input_names=['images'],
                      output_names=['logits'], opset_version=17, dynamo=False)
    import onnxruntime as ort
    session = ort.InferenceSession(str(run_dir / 'classifier.onnx'), providers=['CPUExecutionProvider'])
    with torch.no_grad():
        expected = model(example).numpy()
    actual = session.run(None, {'images': example.numpy()})[0]
    np.testing.assert_allclose(actual, expected, rtol=1e-3, atol=1e-4)
    report['onnxParityMaxAbsoluteError'] = float(np.abs(actual - expected).max())
    report['runtimeProbe'] = {'input': 'zero-normalized-tensor',
                              'logits': session.run(None, {'images': np.zeros((1, 3, SIZE, SIZE), dtype=np.float32)})[0][0].tolist(),
                              'absoluteTolerance': 0.001}
    report['modelSha256'] = file_hash(run_dir / 'classifier.onnx')
    report['completedAtUtc'] = datetime.now(timezone.utc).isoformat()
    (run_dir / 'evaluation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Held-out test accuracy:', report['test']['metrics']['accuracy'], flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--epochs', type=int, default=40)
    parser.add_argument('--task', choices=['disease', 'health'], default='disease')
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error('epochs must be positive')
    train(args.manifest, args.run_dir, args.epochs, args.task)
