"""Train an offline dragon-fruit vs non-dragon-fruit acceptance gate.

Positive samples come from the frozen reviewed quality manifest. Negative
samples come from Caltech-101 and are never copied into the application.
The exported MobileNetV3-small ONNX model is a prerequisite gate; it does not
assign quality grades or disease labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from torchvision.datasets import Caltech101


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ["non-dragon-fruit", "dragon-fruit"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_bucket(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16) % 100


class PresenceDataset(Dataset):
    def __init__(self, positives, negatives, caltech, transform):
        self.items = [("positive", path, 1) for path in positives]
        self.items += [("negative", index, 0) for index in negatives]
        self.caltech = caltech
        self.transform = transform

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        kind, source, label = self.items[index]
        if kind == "positive":
            with Image.open(source) as opened:
                image = opened.convert("RGB")
        else:
            image = self.caltech[source][0].convert("RGB")
        return self.transform(image), label


def metrics(labels, probabilities, threshold):
    labels = np.asarray(labels, dtype=np.int64)
    predicted = (np.asarray(probabilities) >= threshold).astype(np.int64)
    tp = int(((predicted == 1) & (labels == 1)).sum())
    tn = int(((predicted == 0) & (labels == 0)).sum())
    fp = int(((predicted == 1) & (labels == 0)).sum())
    fn = int(((predicted == 0) & (labels == 1)).sum())
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    specificity = tn / max(1, tn + fp)
    return {
        "threshold": float(threshold), "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "accuracy": (tp + tn) / max(1, len(labels)), "precision": precision,
        "recall": recall, "specificity": specificity,
        "f1": 2 * precision * recall / max(1e-12, precision + recall),
    }


def extract_features(encoder, loader):
    values, labels = [], []
    with torch.inference_mode():
        for images, targets in loader:
            values.append(encoder(images).cpu())
            labels.append(targets.cpu())
    return torch.cat(values), torch.cat(labels)


def predict_features(head, features):
    with torch.inference_mode():
        return torch.softmax(head(features), dim=1)[:, 1].cpu().numpy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "local-review/finalized-human-review-2026-10-27/frozen-quality-manifest.json")
    parser.add_argument("--negative-root", type=Path, default=ROOT / "dataset/nonfruit/caltech101")
    parser.add_argument("--output", type=Path, default=ROOT / "training_results/presence-gate-2026-10-30")
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(4)
    args.output.mkdir(parents=True, exist_ok=True)

    rows = json.loads(args.manifest.read_text(encoding="utf-8"))
    split_names = ("train", "val", "test")
    positives = {name: [ROOT / row["image"] for row in rows if row["candidateSplit"] == name] for name in split_names}
    if any(not path.is_file() for paths in positives.values() for path in paths):
        raise FileNotFoundError("The frozen positive manifest references missing images")

    caltech = Caltech101(root=args.negative_root, download=False)
    negatives = {name: [] for name in split_names}
    for index, category_index in enumerate(caltech.y):
        category = caltech.categories[category_index]
        bucket = stable_bucket(f"{category}:{index}")
        split = "train" if bucket < 70 else "val" if bucket < 85 else "test"
        negatives[split].append(index)

    normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(160, scale=(0.72, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=.18, contrast=.18, saturation=.18, hue=.03),
        transforms.ToTensor(), normalize,
    ])
    eval_transform = transforms.Compose([transforms.Resize((160, 160)), transforms.ToTensor(), normalize])

    torch.hub.set_dir(ROOT / "dataset/mendeley-disease/pretrained-cache")
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT).eval()
    feature_count = model.classifier[0].in_features
    model.classifier = nn.Identity()
    encoder = model

    datasets = {
        name: PresenceDataset(positives[name], negatives[name], caltech, train_transform if name == "train" else eval_transform)
        for name in split_names
    }
    loaders = {
        name: DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
        for name, dataset in datasets.items()
    }
    features, targets = {}, {}
    for name in split_names:
        print(f"Extracting {name} features from {len(datasets[name])} images...", flush=True)
        features[name], targets[name] = extract_features(encoder, loaders[name])

    head = nn.Linear(feature_count, 2)
    counts = torch.bincount(targets["train"], minlength=2).float()
    class_weights = counts.sum() / (2 * counts)
    loss_fn = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(head.parameters(), lr=.004, weight_decay=.01)
    best_state, best_loss, stale = None, float("inf"), 0
    history = []
    for epoch in range(args.epochs):
        head.train()
        order = torch.randperm(len(targets["train"]))
        optimizer.zero_grad()
        logits = head(features["train"][order])
        loss = loss_fn(logits, targets["train"][order])
        loss.backward()
        optimizer.step()
        head.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(head(features["val"]), targets["val"]).item())
        history.append({"epoch": epoch + 1, "trainLoss": float(loss.item()), "valLoss": val_loss})
        if val_loss < best_loss - 1e-5:
            best_loss, stale = val_loss, 0
            best_state = {key: value.detach().clone() for key, value in head.state_dict().items()}
        else:
            stale += 1
        if stale >= 30:
            break
    head.load_state_dict(best_state)
    head.eval()

    val_probabilities = predict_features(head, features["val"])
    val_labels = targets["val"].numpy()
    candidates = np.linspace(.50, .995, 496)
    eligible = [threshold for threshold in candidates if metrics(val_labels, val_probabilities, threshold)["specificity"] >= .995]
    threshold = min(eligible, key=lambda item: (-metrics(val_labels, val_probabilities, item)["recall"], item)) if eligible else .995

    model.classifier = head
    model.eval()
    output_path = args.output / "dragonfruit-presence-gate.onnx"
    example = torch.zeros(1, 3, 160, 160)
    torch.onnx.export(model, example, output_path, input_names=["images"], output_names=["probabilities"],
                      opset_version=18, do_constant_folding=True, dynamo=False)

    import onnxruntime as ort
    session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
    actual = session.run(None, {session.get_inputs()[0].name: example.numpy()})[0]
    with torch.inference_mode():
        expected = model(example).numpy()

    split_metrics = {}
    for name in split_names:
        split_metrics[name] = metrics(targets[name].numpy(), predict_features(head, features[name]), threshold)
    report = {
        "status": "evaluated-binary-presence-gate",
        "task": "dragon-fruit-presence",
        "classes": CLASSES,
        "architecture": "ImageNet MobileNetV3-small frozen encoder plus binary linear head",
        "input": {"size": [160, 160], "layout": "NCHW", "normalization": "ImageNet"},
        "threshold": float(threshold),
        "positiveSource": str(args.manifest.relative_to(ROOT)).replace("\\", "/"),
        "negativeSource": "Caltech-101 (101 non-dragon-fruit object categories)",
        "counts": {name: {"positive": len(positives[name]), "negative": len(negatives[name])} for name in split_names},
        "metrics": split_metrics,
        "epochsCompleted": len(history),
        "bestValidationLoss": best_loss,
        "onnxParityMaxAbsoluteError": float(np.max(np.abs(actual - expected))),
        "modelSha256": sha256(output_path),
        "manifestSha256": sha256(args.manifest),
        "createdAtUtc": datetime.now(timezone.utc).isoformat(),
        "history": history,
    }
    (args.output / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("threshold", "counts", "metrics", "modelSha256")}, indent=2))


if __name__ == "__main__":
    main()
